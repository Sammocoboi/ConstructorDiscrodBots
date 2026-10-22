from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts import services
from apps.accounts.models import RefreshSession, User


@pytest.mark.django_db
def test_register_login_me_refresh_logout(api_client: APIClient, mailoutbox):
    register = api_client.post(
        "/api/v1/auth/register",
        {
            "email": "New.User@Example.com",
            "password": "StrongPass123!",
            "display_name": "Новый",
        },
        format="json",
    )
    assert register.status_code == 201, register.data
    assert register.data["user"]["email"] == "new.user@example.com"
    assert len(mailoutbox) == 1
    assert "verify-email" in mailoutbox[0].body

    user = User.objects.get(email="new.user@example.com")
    assert user.email_verified_at is None
    assert user.check_password("StrongPass123!")

    login = api_client.post(
        "/api/v1/auth/login",
        {"email": "new.user@example.com", "password": "StrongPass123!"},
        format="json",
    )
    assert login.status_code == 200, login.data
    assert "access" in login.data
    assert "refresh" not in login.data
    assert login.cookies["refresh_token"].value
    assert RefreshSession.objects.filter(user=user, revoked_at__isnull=True).count() == 1

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    me = api_client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.data["email"] == user.email
    assert me.data["is_email_verified"] is False

    api_client.cookies["refresh_token"] = login.cookies["refresh_token"].value
    refreshed = api_client.post("/api/v1/auth/refresh", {}, format="json")
    assert refreshed.status_code == 200, refreshed.data
    assert "access" in refreshed.data
    assert RefreshSession.objects.filter(user=user, revoked_at__isnull=True).count() == 1

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
    logout = api_client.post("/api/v1/auth/logout", {}, format="json")
    assert logout.status_code == 204
    assert RefreshSession.objects.filter(user=user, revoked_at__isnull=True).count() == 0

    # Старый refresh-token больше не принимается.
    stale = api_client.post("/api/v1/auth/refresh", {}, format="json")
    assert stale.status_code == 401


@pytest.mark.django_db
def test_refresh_without_token_returns_401(api_client: APIClient):
    response = api_client.post("/api/v1/auth/refresh", {}, format="json")
    assert response.status_code == 401
    assert response.data["code"] == "not_authenticated"


@pytest.mark.django_db
def test_email_verification_and_password_reset(api_client: APIClient, user: User, mailoutbox):
    token = services.make_email_verify_token(user)
    verify = api_client.post("/api/v1/auth/email/verify", {"token": token}, format="json")
    assert verify.status_code == 200, verify.data
    user.refresh_from_db()
    assert user.email_verified_at is not None

    reset_request = api_client.post(
        "/api/v1/auth/password/reset/request",
        {"email": user.email},
        format="json",
    )
    assert reset_request.status_code == 202
    assert len(mailoutbox) == 1
    assert "reset-password" in mailoutbox[0].body

    reset_token = services.make_password_reset_token(user)
    confirm = api_client.post(
        "/api/v1/auth/password/reset/confirm",
        {"token": reset_token, "new_password": "AnotherStrongPass456!"},
        format="json",
    )
    assert confirm.status_code == 204
    user.refresh_from_db()
    assert user.check_password("AnotherStrongPass456!")


@pytest.mark.django_db
def test_password_reset_does_not_leak_unknown_email(api_client: APIClient, mailoutbox):
    response = api_client.post(
        "/api/v1/auth/password/reset/request",
        {"email": "nobody@example.com"},
        format="json",
    )
    assert response.status_code == 202
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_email_auth_disabled_returns_403(api_client: APIClient, user: User, mailoutbox, settings):
    """При AUTH_METHODS=discord email-поток выключен и не создаёт сессий (CF-03)."""
    settings.AUTH_METHODS = ["discord"]

    attempts = [
        (
            "/api/v1/auth/register",
            {"email": "blocked@example.com", "password": "StrongPass123!", "display_name": "Блок"},
        ),
        ("/api/v1/auth/login", {"email": user.email, "password": "StrongPass123!"}),
        ("/api/v1/auth/password/reset/request", {"email": user.email}),
        (
            "/api/v1/auth/password/reset/confirm",
            {"token": "irrelevant", "new_password": "AnotherStrongPass456!"},
        ),
    ]

    for path, payload in attempts:
        response = api_client.post(path, payload, format="json")
        assert response.status_code == 403, (path, response.data)
        assert response.data["code"] == "auth_method_disabled"
        assert response.data["details"]["method"] == "email"

    assert not User.objects.filter(email="blocked@example.com").exists()
    assert not RefreshSession.objects.filter(user=user).exists()
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_disabled_email_auth_is_still_throttled(api_client: APIClient, settings):
    """Флаг AUTH_METHODS не отключает throttling email-эндпоинтов."""
    settings.AUTH_METHODS = ["discord"]
    payload = {"email": "nobody@example.com", "password": "StrongPass123!"}

    statuses = [
        api_client.post("/api/v1/auth/login", payload, format="json").status_code
        for _ in range(11)
    ]

    assert statuses[:10] == [403] * 10
    assert statuses[-1] == 429


@pytest.mark.django_db
def test_discord_login_still_works_when_email_auth_disabled(api_client: APIClient, settings):
    settings.AUTH_METHODS = ["discord"]

    response = api_client.get("/api/v1/auth/discord/login")

    assert response.status_code == 302
    assert response["Location"].startswith("https://discord.com/oauth2/authorize")


@pytest.mark.django_db
def test_email_verify_stays_available_when_email_auth_disabled(
    api_client: APIClient, user: User, settings
):
    """Ссылки из уже отправленных писем продолжают работать."""
    settings.AUTH_METHODS = ["discord"]
    token = services.make_email_verify_token(user)

    response = api_client.post("/api/v1/auth/email/verify", {"token": token}, format="json")

    assert response.status_code == 200, response.data


@pytest.mark.django_db
def test_me_update_and_sessions(api_client: APIClient, auth_client: APIClient, user: User):
    update = auth_client.patch(
        "/api/v1/me",
        {"display_name": "Артём Обновлённый", "locale": "en"},
        format="json",
    )
    assert update.status_code == 200, update.data
    assert update.data["display_name"] == "Артём Обновлённый"
    assert update.data["locale"] == "en"

    sessions = auth_client.get("/api/v1/me/sessions")
    assert sessions.status_code == 200
    assert len(sessions.data) == 1

    session_id = sessions.data[0]["id"]
    revoked = auth_client.delete(f"/api/v1/me/sessions/{session_id}")
    assert revoked.status_code == 204
    assert RefreshSession.objects.filter(user=user, revoked_at__isnull=True).count() == 0
