from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.billing.models import Plan


@pytest.mark.django_db
def test_login_and_logout_are_audited(auth_client: APIClient):
    assert AuditLog.objects.filter(action="auth.login").count() == 1

    response = auth_client.post("/api/v1/auth/logout", {}, format="json")
    assert response.status_code == 204
    assert AuditLog.objects.filter(action="auth.logout").count() == 1


@pytest.mark.django_db
def test_password_reset_is_audited(api_client: APIClient, user: User):
    from apps.accounts import services

    token = services.make_password_reset_token(user)
    response = api_client.post(
        "/api/v1/auth/password/reset/confirm",
        {"token": token, "new_password": "AnotherStrongPass456!"},
        format="json",
    )
    assert response.status_code == 204

    entry = AuditLog.objects.get(action="auth.password_reset")
    assert entry.actor == user


@pytest.mark.django_db
def test_stripe_payment_is_audited(api_client: APIClient, user: User, free_plan: Plan):
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_audit_1",
                "subscription": "sub_audit_1",
                "metadata": {"user_id": str(user.id), "plan_code": free_plan.code},
            }
        },
    }
    response = api_client.post("/api/v1/billing/webhook/stripe", event, format="json")
    assert response.status_code == 200, response.data
    assert AuditLog.objects.filter(action="billing.payment_succeeded").count() == 1

    # Повторное событие не создаёт вторую запись аудита.
    api_client.post("/api/v1/billing/webhook/stripe", event, format="json")
    assert AuditLog.objects.filter(action="billing.payment_succeeded").count() == 1


@pytest.mark.django_db
def test_platform_settings_is_singleton():
    from apps.common.models import PlatformSettings

    first = PlatformSettings.load()
    second = PlatformSettings.load()

    assert first.pk == second.pk == 1
    assert PlatformSettings.objects.count() == 1

    first.site_name = "Demo platform"
    first.save()
    assert PlatformSettings.objects.count() == 1
    assert PlatformSettings.load().site_name == "Demo platform"
