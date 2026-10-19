from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.billing.models import Payment, Plan, Subscription


@pytest.mark.django_db
def test_plans_are_public(api_client: APIClient, free_plan: Plan):
    response = api_client.get("/api/v1/plans")
    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert response.data[0]["code"] == "free"


@pytest.mark.django_db
def test_usage_returns_free_plan_limits(auth_client: APIClient, free_plan: Plan):
    response = auth_client.get("/api/v1/me/usage")
    assert response.status_code == 200, response.data
    assert response.data["plan"]["code"] == "free"
    assert response.data["limits"]["bots"] == 1
    assert response.data["executions"] == 0
    assert response.data["api_calls"] == 0


@pytest.mark.django_db
def test_checkout_falls_back_to_mock_without_stripe(
    auth_client: APIClient, free_plan: Plan
):
    response = auth_client.post(
        "/api/v1/billing/checkout", {"plan_code": "free"}, format="json"
    )
    assert response.status_code == 200, response.data
    assert response.data["mock"] is True
    assert "mock-checkout" in response.data["url"]


@pytest.mark.django_db
@override_settings(STRIPE_SECRET_KEY="", STRIPE_WEBHOOK_SECRET="")
def test_stripe_webhook_creates_subscription_idempotently(
    api_client: APIClient, user: User, free_plan: Plan
):
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "subscription": "sub_test_123",
                "metadata": {"user_id": str(user.id), "plan_code": "free"},
            }
        },
    }
    first = api_client.post(
        "/api/v1/billing/webhook/stripe", event, format="json"
    )
    assert first.status_code == 200, first.data
    second = api_client.post(
        "/api/v1/billing/webhook/stripe", event, format="json"
    )
    assert second.status_code == 200, second.data

    assert Subscription.objects.filter(user=user, status=Subscription.Status.ACTIVE).count() == 1
    assert Payment.objects.filter(external_id="cs_test_123").count() == 1


@pytest.mark.django_db
def test_unknown_plan_returns_404(auth_client: APIClient, free_plan: Plan):
    response = auth_client.post(
        "/api/v1/billing/checkout", {"plan_code": "business"}, format="json"
    )
    assert response.status_code == 404
    assert response.data["code"] == "not_found"
