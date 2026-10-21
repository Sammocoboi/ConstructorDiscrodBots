from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.bots.models import Bot
from apps.common.idempotency import IdempotencyMiddleware
from apps.common.models import IdempotencyKey

BOT_PAYLOAD = {"name": "Idempotent bot"}


def _post_bot(client: APIClient, key: str | None, payload: dict | None = None):
    data = payload or BOT_PAYLOAD
    if key:
        return client.post("/api/v1/bots/", data, format="json", HTTP_IDEMPOTENCY_KEY=key)
    return client.post("/api/v1/bots/", data, format="json")


@pytest.mark.django_db
def test_same_key_and_body_replays_response(auth_client: APIClient):
    first = _post_bot(auth_client, "create-bot-1")
    assert first.status_code == 201, first.data

    second = _post_bot(auth_client, "create-bot-1")
    assert second.status_code == 201, second.content
    assert second.json()["id"] == first.data["id"]
    assert second["Idempotent-Replayed"] == "true"
    assert Bot.objects.count() == 1


@pytest.mark.django_db
def test_same_key_with_different_body_returns_conflict(auth_client: APIClient):
    first = _post_bot(auth_client, "create-bot-2")
    assert first.status_code == 201

    second = _post_bot(auth_client, "create-bot-2", {"name": "Another bot"})
    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "idempotency_conflict"
    assert body["request_id"] == second["X-Request-ID"]
    assert Bot.objects.count() == 1


@pytest.mark.django_db
def test_requests_without_key_are_not_deduplicated(auth_client: APIClient):
    assert _post_bot(auth_client, None).status_code == 201
    assert _post_bot(auth_client, None).status_code == 201
    assert Bot.objects.count() == 2


@pytest.mark.django_db
def test_expired_key_is_executed_again(auth_client: APIClient, user):
    first = _post_bot(auth_client, "expired-key")
    assert first.status_code == 201

    IdempotencyKey.objects.filter(user=user, key="expired-key").update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    second = _post_bot(auth_client, "expired-key")
    assert second.status_code == 201
    assert second.data["id"] != first.data["id"]
    assert Bot.objects.count() == 2
    assert IdempotencyKey.objects.filter(user=user, key="expired-key").count() == 1


@pytest.mark.django_db
def test_key_is_scoped_to_user(auth_client: APIClient, other_auth_client: APIClient):
    first = _post_bot(auth_client, "shared-key")
    assert first.status_code == 201

    second = _post_bot(other_auth_client, "shared-key")
    assert second.status_code == 201
    assert second.data["id"] != first.data["id"]
    assert Bot.objects.count() == 2


@pytest.mark.django_db
def test_anonymous_requests_are_not_tracked(api_client: APIClient):
    response = api_client.post(
        "/api/v1/auth/register",
        {"email": "idem@example.com", "password": "StrongPass123!", "display_name": "Идем"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="anonymous-key",
    )
    assert response.status_code == 201
    assert IdempotencyKey.objects.count() == 0


@pytest.mark.django_db
def test_key_in_progress_returns_conflict(auth_client: APIClient, user):
    factory = APIRequestFactory()
    request = factory.post("/api/v1/bots/", BOT_PAYLOAD, format="json")
    fingerprint = IdempotencyMiddleware._fingerprint(request, request.body)

    IdempotencyKey.objects.create(
        user=user,
        key="in-progress",
        request_method="POST",
        request_path="/api/v1/bots/",
        request_hash=fingerprint,
        expires_at=timezone.now() + timedelta(hours=1),
    )
    response = _post_bot(auth_client, "in-progress")
    assert response.status_code == 409
    assert response.json()["code"] == "idempotency_in_progress"


@pytest.mark.django_db
def test_cleanup_command_removes_only_expired_keys(auth_client: APIClient, user):
    _post_bot(auth_client, "fresh-key")
    IdempotencyKey.objects.create(
        user=user,
        key="stale-key",
        request_method="POST",
        request_path="/api/v1/bots",
        request_hash="hash",
        response_status=201,
        response_body={"id": "old"},
        expires_at=timezone.now() - timedelta(hours=1),
    )

    call_command("cleanup_idempotency")

    assert not IdempotencyKey.objects.filter(key="stale-key").exists()
    assert IdempotencyKey.objects.filter(key="fresh-key").exists()
