from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.billing.models import Plan


@pytest.fixture(autouse=True)
def _clear_cache():
    """Изолирует throttling и одноразовые коды между тестами."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="artem@example.com",
        password="StrongPass123!",
        display_name="Артём",
    )


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(
        email="other@example.com",
        password="StrongPass123!",
        display_name="Другой",
    )


@pytest.fixture
def auth_client(api_client: APIClient, user: User) -> APIClient:
    response = api_client.post(
        "/api/v1/auth/login",
        {"email": user.email, "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == 200, response.data
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api_client


@pytest.fixture
def other_auth_client(other_user: User) -> APIClient:
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login",
        {"email": other_user.email, "password": "StrongPass123!"},
        format="json",
    )
    assert response.status_code == 200, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.fixture
def free_plan(db) -> Plan:
    return Plan.objects.create(
        code=Plan.Code.FREE,
        name="Free",
        price_monthly=0,
        limits={"bots": 1, "guilds_per_bot": 3, "executions_per_month": 10_000},
        sort_order=1,
    )
