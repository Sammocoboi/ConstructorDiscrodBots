"""Регрессия object-level доступа (FR §10.2, ART-8)."""

from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import Invoice
from apps.bots.models import Bot, BotGuild, BotVersion
from apps.notifications.models import Notification


@pytest.fixture
def bot(user) -> Bot:
    return Bot.objects.create(owner=user, name="Мой бот")


@pytest.mark.django_db
def test_other_user_cannot_read_bot_guild(other_auth_client: APIClient, bot: Bot):
    guild = BotGuild.objects.create(bot=bot, guild_id="123", guild_name="Сервер")

    response = other_auth_client.get(f"/api/v1/bots/{bot.id}/guilds/{guild.guild_id}")
    assert response.status_code == 404


@pytest.mark.django_db
def test_other_user_cannot_update_bot_guild(other_auth_client: APIClient, bot: Bot):
    guild = BotGuild.objects.create(bot=bot, guild_id="456", guild_name="Сервер")

    response = other_auth_client.patch(
        f"/api/v1/bots/{bot.id}/guilds/{guild.guild_id}",
        {"guild_name": "Угнан"},
        format="json",
    )
    assert response.status_code == 404
    guild.refresh_from_db()
    assert guild.guild_name == "Сервер"


@pytest.mark.django_db
def test_other_user_cannot_read_bot_version(other_auth_client: APIClient, bot: Bot):
    version = BotVersion.objects.create(bot=bot, version_number=1, content={"a": 1})

    response = other_auth_client.get(f"/api/v1/bots/{bot.id}/versions/{version.id}")
    assert response.status_code == 404


@pytest.mark.django_db
def test_other_user_cannot_start_or_stop_foreign_bot(other_auth_client: APIClient, bot: Bot):
    for action in ("start", "stop", "restart"):
        response = other_auth_client.post(f"/api/v1/bots/{bot.id}/{action}/", {}, format="json")
        assert response.status_code == 404
    assert other_auth_client.get(f"/api/v1/bots/{bot.id}/status/").status_code == 404


@pytest.mark.django_db
def test_other_user_cannot_revoke_foreign_session(
    auth_client: APIClient, other_auth_client: APIClient
):
    sessions = auth_client.get("/api/v1/me/sessions")
    assert sessions.status_code == 200
    session_id = sessions.data[0]["id"]

    response = other_auth_client.delete(f"/api/v1/me/sessions/{session_id}")
    assert response.status_code == 404


@pytest.mark.django_db
def test_invoices_are_scoped_to_user(auth_client: APIClient, other_auth_client: APIClient, user):
    Invoice.objects.create(
        user=user,
        number="INV-1",
        amount=10,
        status=Invoice.Status.PAID,
    )

    own = auth_client.get("/api/v1/billing/invoices")
    assert own.status_code == 200
    assert len(own.data["results"]) == 1

    foreign = other_auth_client.get("/api/v1/billing/invoices")
    assert foreign.status_code == 200
    assert foreign.data["results"] == []


@pytest.mark.django_db
def test_other_user_cannot_mark_foreign_notification_read(other_auth_client: APIClient, user):
    notification = Notification.objects.create(user=user, type="test", payload={"a": 1})

    response = other_auth_client.post(
        f"/api/v1/notifications/{notification.id}/read/", {}, format="json"
    )
    assert response.status_code == 404
    assert other_auth_client.get("/api/v1/notifications/").data["results"] == []


@pytest.mark.django_db
def test_soft_deleted_account_cannot_login(api_client: APIClient, user):
    user.deleted_at = timezone.now()
    user.is_active = False
    user.save(update_fields=["deleted_at", "is_active", "updated_at"])

    response = api_client.post(
        "/api/v1/auth/login",
        {"email": user.email, "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == 401
