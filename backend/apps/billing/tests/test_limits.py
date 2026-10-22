from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing import services
from apps.billing.models import Plan, Subscription
from apps.common.exceptions import LimitExceeded
from apps.notifications.models import Notification


@pytest.mark.django_db
def test_bot_limit_blocks_creation(auth_client: APIClient, free_plan: Plan):
    first = auth_client.post("/api/v1/bots/", {"name": "Первый"}, format="json")
    assert first.status_code == 201, first.data

    second = auth_client.post("/api/v1/bots/", {"name": "Второй"}, format="json")
    assert second.status_code == 403, second.data
    assert second.data["code"] == "limit_exceeded"
    assert second.data["details"]["limit"] == "bots"


@pytest.mark.django_db
def test_no_bot_limit_when_plan_has_no_limit(auth_client: APIClient, free_plan: Plan):
    free_plan.limits = {}
    free_plan.save(update_fields=["limits"])

    assert auth_client.post("/api/v1/bots/", {"name": "A"}, format="json").status_code == 201
    assert auth_client.post("/api/v1/bots/", {"name": "B"}, format="json").status_code == 201


@pytest.mark.django_db
def test_usage_warning_is_created_once_at_80_percent(user, free_plan: Plan):
    free_plan.limits = {"bots": 1, "executions_per_month": 10}
    free_plan.save(update_fields=["limits"])

    services.record_usage(user, executions=8)
    notification = Notification.objects.get(user=user, type="limit_warning_executions_per_month")
    assert notification.payload["percent"] == 80

    services.record_usage(user, executions=1)
    assert (
        Notification.objects.filter(user=user, type="limit_warning_executions_per_month").count()
        == 1
    )


@pytest.mark.django_db
def test_execution_limit_blocks_at_100_percent(user, free_plan: Plan):
    free_plan.limits = {"bots": 1, "executions_per_month": 10}
    free_plan.save(update_fields=["limits"])

    services.record_usage(user, executions=9)
    summary = services.check_execution_limit(user)
    assert summary["execution_blocked"] is False
    assert summary["executions_percent"] == 90

    services.record_usage(user, executions=1)
    with pytest.raises(LimitExceeded) as exc:
        services.check_execution_limit(user)
    assert exc.value.limit == "executions_per_month"


@pytest.mark.django_db
def test_usage_endpoint_exposes_limit_state(auth_client: APIClient, user, free_plan: Plan):
    free_plan.limits = {"bots": 1, "executions_per_month": 10}
    free_plan.save(update_fields=["limits"])
    services.record_usage(user, executions=8)

    response = auth_client.get("/api/v1/me/usage")
    assert response.status_code == 200, response.data
    assert response.data["executions_percent"] == 80
    assert response.data["execution_blocked"] is False
    assert response.data["bots_used"] == 0
    assert "executions_per_month" in response.data["warnings"]


@pytest.mark.django_db
def test_expired_subscription_degrades_to_free(user, free_plan: Plan):
    pro = Plan.objects.create(
        code=Plan.Code.PRO,
        name="Pro",
        price_monthly=10,
        limits={"bots": 5, "executions_per_month": 100},
        sort_order=2,
    )
    subscription = Subscription.objects.create(
        user=user,
        plan=pro,
        status=Subscription.Status.ACTIVE,
        current_period_end=timezone.now() - timedelta(days=1),
    )

    plan = services.get_active_plan(user)
    assert plan is not None
    assert plan.code == Plan.Code.FREE
    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.EXPIRED


@pytest.mark.django_db
def test_active_subscription_uses_paid_plan(user, free_plan: Plan):
    pro = Plan.objects.create(
        code=Plan.Code.PRO,
        name="Pro",
        price_monthly=10,
        limits={"bots": 5, "executions_per_month": 100},
        sort_order=2,
    )
    Subscription.objects.create(
        user=user,
        plan=pro,
        status=Subscription.Status.ACTIVE,
        current_period_end=timezone.now() + timedelta(days=10),
    )

    plan = services.get_active_plan(user)
    assert plan is not None
    assert plan.code == Plan.Code.PRO
