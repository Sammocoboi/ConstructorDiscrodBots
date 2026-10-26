from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.bots.models import Bot, BotGuild, RuntimeCommand
from apps.bots.services import DiscordAPIError
from apps.common.crypto import decrypt_secret


@pytest.mark.django_db
def test_validate_token_returns_frontend_shape(auth_client: APIClient):
    inspected = {
        "user": {"id": "42", "username": "test-bot", "global_name": "Test Bot", "bot": True},
        "application": {"id": "app-42"},
        "guilds": [{"id": "1"}, {"id": "2"}],
    }
    with patch("apps.bots.views.inspect_bot_token", return_value=inspected):
        response = auth_client.post(
            "/api/v1/bots/validate-token/",
            {"token": "  bot-token  "},
            format="json",
        )

    assert response.status_code == 200, response.data
    assert response.data == {
        "valid": True,
        "username": "Test Bot",
        "applicationId": "app-42",
        "avatarColor": "#5865f2",
        "guildsCount": 2,
    }


@pytest.mark.django_db
def test_validate_token_rejects_invalid_token(auth_client: APIClient):
    with patch(
        "apps.bots.views.inspect_bot_token",
        side_effect=DiscordAPIError("Discord rejected the bot token"),
    ):
        response = auth_client.post(
            "/api/v1/bots/validate-token/",
            {"token": "bad-token"},
            format="json",
        )

    assert response.status_code == 400
    assert response.data["valid"] is False
    assert "rejected" in response.data["detail"]


@pytest.mark.django_db
def test_replace_token_encrypts_and_enqueues_reload(auth_client: APIClient, user):
    bot = Bot.objects.create(owner=user, name="Token bot", desired_state="running")

    with (
        patch(
            "apps.bots.services.validate_bot_token",
            return_value={"id": "99", "username": "fresh-bot", "bot": True},
        ),
        patch("apps.bots.services.fetch_bot_application", return_value={"id": "app-99"}),
    ):
        response = auth_client.post(
            f"/api/v1/bots/{bot.id}/token/",
            {"token": "fresh-token"},
            format="json",
        )

    assert response.status_code == 200, response.data
    assert response.data["discord_application_id"] == "app-99"
    assert response.data["discord_bot_user_id"] == "99"
    assert "token_encrypted" not in response.data

    bot.refresh_from_db()
    assert bot.token_encrypted
    assert decrypt_secret(bot.token_encrypted) == "fresh-token"
    assert RuntimeCommand.objects.filter(
        bot=bot, command=RuntimeCommand.Command.RELOAD
    ).count() == 1


@pytest.mark.django_db
def test_replace_token_is_scoped_to_owner(
    other_auth_client: APIClient,
    user,
):
    bot = Bot.objects.create(owner=user, name="Private bot")

    response = other_auth_client.post(
        f"/api/v1/bots/{bot.id}/token/",
        {"token": "stolen-token"},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_guild_sync_upserts_and_marks_left(
    api_client: APIClient,
    user,
    settings,
):
    settings.RUNTIME_SERVICE_TOKEN = "runtime-secret"
    bot = Bot.objects.create(owner=user, name="Guild bot")

    first = api_client.post(
        f"/api/v1/bots/{bot.id}/guilds/sync",
        {"guilds": [{"id": "111", "name": "Server One"}]},
        format="json",
        HTTP_X_RUNTIME_TOKEN="runtime-secret",
    )

    assert first.status_code == 200, first.data
    assert first.data == {"synced": 1}
    guild = BotGuild.objects.get(bot=bot, guild_id="111")
    assert guild.guild_name == "Server One"
    assert guild.left_at is None

    second = api_client.post(
        f"/api/v1/bots/{bot.id}/guilds/sync",
        {"guilds": []},
        format="json",
        HTTP_X_RUNTIME_TOKEN="runtime-secret",
    )

    assert second.status_code == 200, second.data
    guild.refresh_from_db()
    assert guild.left_at is not None


@pytest.mark.django_db
def test_guild_sync_requires_runtime_secret(api_client: APIClient, user, settings):
    settings.RUNTIME_SERVICE_TOKEN = "runtime-secret"
    bot = Bot.objects.create(owner=user, name="Guild bot")

    response = api_client.post(
        f"/api/v1/bots/{bot.id}/guilds/sync",
        {"guilds": []},
        format="json",
        HTTP_X_RUNTIME_TOKEN="wrong-secret",
    )

    assert response.status_code == 403

    settings.RUNTIME_SERVICE_TOKEN = ""
    response = api_client.post(
        f"/api/v1/bots/{bot.id}/guilds/sync",
        {"guilds": []},
        format="json",
        HTTP_X_RUNTIME_TOKEN="any",
    )
    assert response.status_code == 403
