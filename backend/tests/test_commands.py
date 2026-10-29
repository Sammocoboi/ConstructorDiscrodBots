import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.bots.models import Bot, BotGuild
from apps.commands.permissions_cooldowns import (
    CommandAccessRule,
    CommandCooldownTracker,
)
from apps.commands.registry import CommandLibraryRegistry


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

    conflict = CommandLibraryRegistry.check_name_conflict(existing, "ping")
    assert conflict["has_conflict"] is True
    assert conflict["suggested_name"] == "ping_2"

    no_conflict = CommandLibraryRegistry.check_name_conflict(existing, "kick")
    assert no_conflict["has_conflict"] is False


@pytest.mark.django_db
def test_install_commands_into_bot_with_auto_modules():
    client = APIClient()
    user = get_user_model().objects.create_user(
        email="user-c@example.com", password="test-pass", display_name="User C"
    )
    client.force_authenticate(user=user)
    bot = Bot.objects.create(name="CmdBot", owner=user)
    guild = BotGuild.objects.create(bot=bot, guild_id="123456")

    payload = {"slugs": ["warn"], "guild_id": "123456", "action_on_conflict": "replace"}

    resp = client.post(f"/api/v1/bots/{bot.id}/commands/install", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["installed_count"] == 1
    assert "moderation" in resp.data["auto_enabled_modules"]

    guild.refresh_from_db()
    assert "moderation" in guild.enabled_modules

    bot.refresh_from_db()
    assert "warn" in bot.profile["installed_commands"]


def test_command_access_rules_allow_deny():
    rule = CommandAccessRule(
        default_member_permissions="4", allowed_roles=["role_mod"], denied_users=["banned_user_1"]
    )

    ok, err = rule.is_allowed(
        user_id="banned_user_1", user_roles=["role_mod"], channel_id="c1", user_permissions_int=4
    )
    assert ok is False
    assert "недостаточно прав" in err

    ok, err = rule.is_allowed(
        user_id="user_2", user_roles=["role_member"], channel_id="c1", user_permissions_int=4
    )
    assert ok is False

    ok, err = rule.is_allowed(
        user_id="user_mod", user_roles=["role_mod"], channel_id="c1", user_permissions_int=4
    )
    assert ok is True
    assert err is None


def test_command_cooldown_tracker():
    tracker = CommandCooldownTracker()

    avail, rem = tracker.check_and_update("daily", "user", "u1", cooldown_seconds=60)
    assert avail is True
    assert rem == 0.0

    avail, rem = tracker.check_and_update("daily", "user", "u1", cooldown_seconds=60)
    assert avail is False
    assert rem > 50.0
