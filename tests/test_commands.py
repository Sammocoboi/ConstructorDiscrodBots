"""
Тесты библиотеки команд, разрешения зависимостей, конфликтов и кулдаунов (SAN-8, SAN-10, SAN-12).
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from backend.apps.bots.models import Bot, BotGuild
from backend.apps.commands.registry import CommandLibraryRegistry
from backend.apps.commands.permissions_cooldowns import (
    CommandAccessRule,
    CommandCooldownTracker,
)


def test_command_library_has_70_plus_commands():
    commands = CommandLibraryRegistry.list_commands()
    assert len(commands) >= 70, f"Ожидалось не менее 70 команд по ТЗ, найдено {len(commands)}"


def test_command_dependency_resolution():
    dep_warn = CommandLibraryRegistry.resolve_dependencies("warn")
    assert dep_warn["required_module"] == "moderation"
    assert dep_warn["needs_module_activation"] is True

    dep_ping = CommandLibraryRegistry.resolve_dependencies("ping")
    assert dep_ping["required_module"] is None
    assert dep_ping["needs_module_activation"] is False


def test_command_name_conflict_resolution():
    existing = ["ping", "ban", "warn"]
    
    # Конфликт с ping
    conflict = CommandLibraryRegistry.check_name_conflict(existing, "ping")
    assert conflict["has_conflict"] is True
    assert conflict["suggested_name"] == "ping_2"

    # Нет конфликта
    no_conflict = CommandLibraryRegistry.check_name_conflict(existing, "kick")
    assert no_conflict["has_conflict"] is False


@pytest.mark.django_db
def test_install_commands_into_bot_with_auto_modules():
    client = APIClient()
    bot = Bot.objects.create(name="CmdBot", owner_id="user-c")
    guild = BotGuild.objects.create(bot=bot, guild_id="123456")

    # Установка команды warn (требует модуль moderation)
    payload = {
        "slugs": ["warn"],
        "guild_id": "123456",
        "action_on_conflict": "replace"
    }

    resp = client.post(f"/api/v1/bots/{bot.id}/commands/install", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["installed_count"] == 1
    assert "moderation" in resp.data["auto_enabled_modules"]

    # Проверяем, что модуль moderation был автоматически включен на сервере
    guild.refresh_from_db()
    assert "moderation" in guild.enabled_modules

    # Проверяем команду в профиле бота
    bot.refresh_from_db()
    assert "warn" in bot.profile["installed_commands"]


def test_command_access_rules_allow_deny():
    rule = CommandAccessRule(
        default_member_permissions="4",  # BAN_MEMBERS
        allowed_roles=["role_mod"],
        denied_users=["banned_user_1"]
    )

    # 1. Запрещенный пользователь
    ok, err = rule.is_allowed(user_id="banned_user_1", user_roles=["role_mod"], channel_id="c1", user_permissions_int=4)
    assert ok is False
    assert "недостаточно прав" in err

    # 2. Пользователь без нужной роли
    ok, err = rule.is_allowed(user_id="user_2", user_roles=["role_member"], channel_id="c1", user_permissions_int=4)
    assert ok is False

    # 3. Пользователь с нужной ролью и правами
    ok, err = rule.is_allowed(user_id="user_mod", user_roles=["role_mod"], channel_id="c1", user_permissions_int=4)
    assert ok is True
    assert err is None


def test_command_cooldown_tracker():
    tracker = CommandCooldownTracker()
    
    # 1-е использование: разрешено
    avail, rem = tracker.check_and_update("daily", "user", "u1", cooldown_seconds=60)
    assert avail is True
    assert rem == 0.0

    # 2-е использование сразу же: заблокировано кулдауном
    avail, rem = tracker.check_and_update("daily", "user", "u1", cooldown_seconds=60)
    assert avail is False
    assert rem > 50.0
