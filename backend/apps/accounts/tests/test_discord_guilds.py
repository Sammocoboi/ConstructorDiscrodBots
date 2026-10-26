from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import OAuthAccount, User
from apps.bots.models import Bot, BotGuild
from apps.common.crypto import encrypt_secret


@pytest.fixture(autouse=True)
def clear_django_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_discord_guilds_requires_authentication(api_client: APIClient):
    response = api_client.get("/api/v1/me/discord-guilds")
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_without_discord_oauth_returns_empty_list(auth_client: APIClient):
    response = auth_client.get("/api/v1/me/discord-guilds")
    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
def test_user_guilds_filters_unmanageable_guilds(auth_client: APIClient, user: User):
    """CF-05: Оставлять только owner === true или permissions & MANAGE_GUILD (0x20) / ADMINISTRATOR (0x8)."""
    OAuthAccount.objects.create(
        user=user,
        provider=OAuthAccount.Provider.DISCORD,
        provider_user_id="discord_12345",
        access_token_encrypted=encrypt_secret("test_access_token"),
    )

    mock_discord_guilds = [
        # 1. Владелец сервера (owner: True) -> ДОЛЖЕН БЫТЬ
        {
            "id": "111111111111111111",
            "name": "Owner Server",
            "icon": "icon_1",
            "owner": True,
            "permissions": "0",
            "approximate_member_count": 120,
        },
        # 2. Не владелец, но есть MANAGE_GUILD (0x20 = 32) -> ДОЛЖЕН БЫТЬ
        {
            "id": "222222222222222222",
            "name": "Manager Server",
            "icon": "icon_2",
            "owner": False,
            "permissions": "32",
            "approximate_member_count": 450,
        },
        # 3. Не владелец, но есть ADMINISTRATOR (0x8 = 8) -> ДОЛЖЕН БЫТЬ
        {
            "id": "333333333333333333",
            "name": "Admin Server",
            "icon": "icon_3",
            "owner": False,
            "permissions": "8",
            "approximate_member_count": 890,
        },
        # 4. Обычный участник без MANAGE_GUILD и ADMINISTRATOR -> НЕ ДОЛЖЕН БЫТЬ
        {
            "id": "444444444444444444",
            "name": "Member Only Server",
            "icon": "icon_4",
            "owner": False,
            "permissions": "104324673",  # обычные права пользователя
            "approximate_member_count": 25000,
        },
    ]

    with patch("integrations.discord.client.DiscordRestClient.get_user_guilds", return_value=mock_discord_guilds):
        response = auth_client.get("/api/v1/me/discord-guilds")

    assert response.status_code == 200
    returned_ids = [g["id"] for g in response.data]

    assert "111111111111111111" in returned_ids
    assert "222222222222222222" in returned_ids
    assert "333333333333333333" in returned_ids
    assert "444444444444444444" not in returned_ids
    assert len(response.data) == 3

    # Проверка структуры каждого объекта (CF-05 п. 3)
    owner_guild = next(g for g in response.data if g["id"] == "111111111111111111")
    assert owner_guild["canManage"] is True
    assert owner_guild["owner"] is True
    assert owner_guild["botAdded"] is False
    assert owner_guild["memberCount"] == 120
    assert "iconColor" in owner_guild
    assert owner_guild["channels"] == []
    assert owner_guild["roles"] == []


@pytest.mark.django_db
def test_guilds_cache_and_invalidation_on_bot_added(auth_client: APIClient, user: User):
    """CF-05: Кэш 60 секунд, инвалидация при повторном входе и после добавления бота."""
    OAuthAccount.objects.create(
        user=user,
        provider=OAuthAccount.Provider.DISCORD,
        provider_user_id="discord_12345",
        access_token_encrypted=encrypt_secret("test_access_token"),
    )

    mock_discord_guilds = [
        {
            "id": "111111111111111111",
            "name": "Cached Server",
            "owner": True,
            "permissions": "0",
            "approximate_member_count": 50,
        }
    ]

    with patch("integrations.discord.client.DiscordRestClient.get_user_guilds", return_value=mock_discord_guilds) as mock_fetch:
        resp1 = auth_client.get("/api/v1/me/discord-guilds")
        assert resp1.status_code == 200
        assert resp1.data[0]["botAdded"] is False
        assert mock_fetch.call_count == 1

        # Второй запрос возвращается из кэша, mock_fetch не вызывается
        resp2 = auth_client.get("/api/v1/me/discord-guilds")
        assert resp2.status_code == 200
        assert mock_fetch.call_count == 1

        # Добавляем бота на сервер -> сигнал инвалидирует кэш
        bot = Bot.objects.create(name="Bot 1", owner=user)
        BotGuild.objects.create(
            bot=bot,
            guild_id="111111111111111111",
            guild_name="Cached Server",
            settings={"channels": [{"id": "c1", "name": "general", "type": "text"}]},
        )

        # Третий запрос обращается заново и видит botAdded: True и каналы
        resp3 = auth_client.get("/api/v1/me/discord-guilds")
        assert resp3.status_code == 200
        assert mock_fetch.call_count == 2
        assert resp3.data[0]["botAdded"] is True
        assert len(resp3.data[0]["channels"]) == 1
        assert resp3.data[0]["channels"][0]["name"] == "general"
