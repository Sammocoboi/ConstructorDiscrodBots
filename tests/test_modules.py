"""
Тесты модулей, JSON Schema настроек и проверки прав (SAN-7).
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from backend.apps.bots.models import Bot, BotGuild
from backend.apps.modules.registry import ModuleRegistry


def test_modules_registry_contains_all_core_modules():
    modules = ModuleRegistry.list_all()
    slugs = [m["slug"] for m in modules]
    assert "welcomes" in slugs
    assert "moderation" in slugs
    assert "antispam" in slugs
    assert "tickets" in slugs
    assert "levels" in slugs
    assert "economy" in slugs
    assert "logging" in slugs
    assert "roles" in slugs
    assert "fun" in slugs
    assert "automation" in slugs
    assert "giveaways" in slugs


def test_validate_module_settings_json_schema():
    # Валидные настройки welcomes
    valid_settings = {
        "welcome_channel_id": "123456789",
        "welcome_message": "Привет!",
        "welcome_embed": True,
        "autorole_id": None
    }
    # Не должно выбрасывать исключений
    ModuleRegistry.validate_settings("welcomes", valid_settings)

    # Невалидные настройки (некорректный тип welcome_embed: строка вместо bool)
    invalid_settings = {
        "welcome_embed": "not_a_boolean"
    }
    with pytest.raises(Exception):
        ModuleRegistry.validate_settings("welcomes", invalid_settings)


@pytest.mark.django_db
def test_bot_module_enable_and_settings_update():
    client = APIClient()
    bot = Bot.objects.create(name="ModuleBot", owner_id="user-m")
    
    payload = {
        "guild_id": "999111222",
        "enabled": True,
        "settings": {
            "welcome_channel_id": "555666777",
            "welcome_message": "Добро пожаловать, {user.mention}!",
            "welcome_embed": True
        },
        "bot_permissions": 268453888,
        "bot_highest_role_pos": 20,
        "target_role_pos": 10
    }

    resp = client.put(f"/api/v1/bots/{bot.id}/modules/welcomes", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["enabled"] is True
    assert resp.data["validation"]["valid"] is True

    # Проверяем сохранение в BotGuild
    guild = BotGuild.objects.get(bot=bot, guild_id="999111222")
    assert "welcomes" in guild.enabled_modules
    assert guild.settings["welcomes"]["welcome_channel_id"] == "555666777"
