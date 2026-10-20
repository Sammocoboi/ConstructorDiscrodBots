"""
Интеграционные тесты API ботов (CRUD, токен, лимиты, invite, синхронизация) (SAN-1..SAN-4, SAN-9).
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status

from backend.apps.bots.models import Bot, BotGuild, BotStatus, DesiredState
from backend.apps.bots.services import BotService


@pytest.mark.django_db
def test_create_and_list_bots():
    client = APIClient()
    # 1. Создание бота
    resp = client.post("/api/v1/bots/", {"name": "TestBot", "owner_id": "user-123"}, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    bot_id = resp.data["id"]
    assert resp.data["name"] == "TestBot"
    assert resp.data["status"] == "stopped"

    # 2. Список ботов
    list_resp = client.get(f"/api/v1/bots/?owner_id=user-123")
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.data) == 1
    assert list_resp.data[0]["id"] == bot_id


@pytest.mark.django_db
def test_plan_limit_enforcement():
    client = APIClient()
    # Free тариф разрешает только 1 бота
    client.post("/api/v1/bots/", {"name": "Bot1", "owner_id": "user-free", "plan_name": "free"}, format="json")
    
    # Вторая попытка должна вернуть 403 Forbidden
    resp = client.post("/api/v1/bots/", {"name": "Bot2", "owner_id": "user-free", "plan_name": "free"}, format="json")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "Превышен лимит ботов" in resp.data["detail"]


@pytest.mark.django_db
def test_validate_and_update_token():
    client = APIClient()
    bot = Bot.objects.create(name="BotBeforeToken", owner_id="user-t")

    mock_bot_data = {
        "id": "999888777",
        "username": "VerifiedDiscordBot",
        "discriminator": "0001",
        "avatar": "hash123",
        "bot": True,
        "flags": 0
    }

    with patch("backend.integrations.discord.client.DiscordRestClient.get_current_bot_user", return_value=mock_bot_data):
        # Валидация токена
        val_resp = client.post(f"/api/v1/bots/{bot.id}/token/validate/", {"token": "valid_secret_token_1234567890"}, format="json")
        assert val_resp.status_code == status.HTTP_200_OK
        assert val_resp.data["valid"] is True
        assert val_resp.data["bot"]["username"] == "VerifiedDiscordBot"

        # Обновление токена без потери настроек
        upd_resp = client.put(f"/api/v1/bots/{bot.id}/token/", {"token": "valid_secret_token_1234567890"}, format="json")
        assert upd_resp.status_code == status.HTTP_200_OK
        assert upd_resp.data["name"] == "VerifiedDiscordBot"
        assert "••••" in upd_resp.data["token_masked"]
        assert upd_resp.data["discord_application_id"] == "999888777"


@pytest.mark.django_db
def test_start_stop_restart_bot():
    client = APIClient()
    bot = Bot.objects.create(name="LifecycleBot", owner_id="user-l")
    bot.set_token("sample_token_for_lifecycle_test")
    bot.save()

    # Start
    res_start = client.post(f"/api/v1/bots/{bot.id}/start/")
    assert res_start.status_code == status.HTTP_200_OK
    bot.refresh_from_db()
    assert bot.desired_state == "running"
    assert bot.status == "starting"

    # Stop
    res_stop = client.post(f"/api/v1/bots/{bot.id}/stop/")
    assert res_stop.status_code == status.HTTP_200_OK
    bot.refresh_from_db()
    assert bot.desired_state == "stopped"
    assert bot.status == "stopped"


@pytest.mark.django_db
def test_invite_url():
    client = APIClient()
    bot = Bot.objects.create(name="InviteBot", owner_id="user-inv", discord_application_id="1122334455")
    
    resp = client.get(f"/api/v1/bots/{bot.id}/invite-url/")
    assert resp.status_code == status.HTTP_200_OK
    assert "https://discord.com/oauth2/authorize" in resp.data["invite_url"]
    assert "client_id=1122334455" in resp.data["invite_url"]
    assert resp.data["permissions_integer"] > 0


@pytest.mark.django_db
def test_commands_sync_bulk_and_hash():
    client = APIClient()
    bot = Bot.objects.create(name="SyncBot", owner_id="user-s", discord_application_id="5544332211")
    bot.set_token("dummy_token_123456789012345")
    bot.save()

    commands = [{"name": "ping", "description": "ping command"}]

    with patch("backend.integrations.discord.client.DiscordRestClient.bulk_overwrite_global_commands", return_value=commands):
        # 1-я синхронизация: регистрирует
        res1 = client.post(f"/api/v1/bots/{bot.id}/commands/sync/", {"commands": commands}, format="json")
        assert res1.status_code == status.HTTP_200_OK
        assert res1.data["status"] == "synchronized"
        assert res1.data["registered_count"] == 1

        # 2-я синхронизация с теми же командами: пропускает по хешу (FR-4.5)
        res2 = client.post(f"/api/v1/bots/{bot.id}/commands/sync/", {"commands": commands}, format="json")
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["status"] == "skipped"
        assert "хеш совпадает" in res2.data["message"]
