from __future__ import annotations

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts import services


def _state_from_location(location: str) -> str:
    return parse_qs(urlparse(location).query)["state"][0]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/app/bots/1", "/app/bots/1"),
        ("/app?tab=status", "/app?tab=status"),
        ("https://evil.example/app", ""),
        ("//evil.example/app", ""),
        ("/\\evil.example/app", ""),
        ("/app\nLocation: https://evil.example", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_safe_next_path(value, expected):
    assert services.safe_next_path(value) == expected


@pytest.mark.django_db
def test_discord_login_redirects_and_stores_next(api_client: APIClient, settings):
    settings.DISCORD_CLIENT_ID = "client-id"
    settings.DISCORD_REDIRECT_URI = "http://localhost:8000/api/v1/auth/discord/callback"

    response = api_client.get("/api/v1/auth/discord?next=%2Fapp%2Fbots%2F1")

    assert response.status_code == 302
    assert response["Location"].startswith("https://discord.com/oauth2/authorize")
    state = _state_from_location(response["Location"])
    assert cache.get(f"discord:state:{state}") == {"next": "/app/bots/1"}


@pytest.mark.django_db
def test_discord_login_alias_works(api_client: APIClient, settings):
    settings.DISCORD_CLIENT_ID = "client-id"

    response = api_client.get("/api/v1/auth/discord")

    assert response.status_code == 302
    assert response["Location"].startswith("https://discord.com/oauth2/authorize")


@pytest.mark.django_db
def test_discord_callback_rejects_unknown_state(api_client: APIClient, settings):
    settings.FRONTEND_URL = "http://localhost:5173"

    response = api_client.get("/api/v1/auth/discord/callback?state=unknown&code=code")

    assert response.status_code == 302
    assert response["Location"].startswith(
        "http://localhost:5173/auth/callback/discord?error=invalid_state"
    )


@pytest.mark.django_db
def test_discord_callback_returns_code_and_next(api_client: APIClient, settings, user):
    settings.FRONTEND_URL = "http://localhost:5173"
    state = services.build_discord_state("/app/bots/1")

    with (
        patch.object(
            services,
            "exchange_discord_code",
            return_value={"access_token": "discord-access-token"},
        ),
        patch.object(services, "fetch_discord_user", return_value={"id": "42"}),
        patch.object(services, "get_or_create_discord_user", return_value=user),
        patch.object(services, "create_discord_login_code", return_value="one-time-code"),
    ):
        response = api_client.get(
            f"/api/v1/auth/discord/callback?state={state}&code=discord-code"
        )

    assert response.status_code == 302
    assert response["Location"] == (
        "http://localhost:5173/auth/callback/discord"
        "?code=one-time-code&next=%2Fapp%2Fbots%2F1"
    )


@pytest.mark.django_db
def test_discord_exchange_returns_access_token_alias(api_client: APIClient, user):
    with patch.object(services, "consume_discord_login_code", return_value=user):
        response = api_client.post(
            "/api/v1/auth/discord/exchange",
            {"code": "one-time-code"},
            format="json",
        )

    assert response.status_code == 200, response.data
    assert response.data["access"] == response.data["access_token"]
    assert response.cookies["refresh_token"].value


@pytest.mark.django_db
def test_register_returns_access_token_and_cookie(api_client: APIClient, mailoutbox):
    response = api_client.post(
        "/api/v1/auth/register",
        {
            "email": "new-user@example.com",
            "password": "StrongPass123!",
            "display_name": "Новый",
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["access"] == response.data["access_token"]
    assert response.cookies["refresh_token"].value
