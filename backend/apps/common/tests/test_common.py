from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.common.utils import uuid7


def test_uuid7_version_and_variant():
    value = uuid7()
    assert isinstance(value, uuid.UUID)
    assert value.version == 7
    assert value.variant == uuid.RFC_4122


@pytest.mark.django_db
def test_health_and_request_id(api_client: APIClient):
    response = api_client.get("/api/v1/health", HTTP_X_REQUEST_ID="test-request-id")
    assert response.status_code == 200
    assert response.data == {"status": "ok"}
    assert response["X-Request-ID"] == "test-request-id"


@pytest.mark.django_db
def test_error_format_for_unauthenticated_request(api_client: APIClient):
    response = api_client.get("/api/v1/me")
    assert response.status_code == 401
    assert set(response.data) == {"code", "message", "details", "request_id"}
    assert response.data["code"] == "not_authenticated"
    assert response.data["request_id"] == response["X-Request-ID"]
