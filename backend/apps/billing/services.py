"""Billing business logic and Stripe integration."""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime, timezone as dt_timezone

import stripe
from django.conf import settings

from .models import Plan, Subscription, UsageCounter

logger = logging.getLogger(__name__)


def stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def current_period() -> tuple[date, date]:
    today = date.today()
    last_day = monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


def get_active_plan(user) -> Plan:
    subscription = (
        Subscription.objects.filter(
            user=user,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING],
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    if subscription and subscription.plan.is_active:
        return subscription.plan
    return Plan.objects.filter(code=Plan.Code.FREE, is_active=True).first()


def get_usage(user) -> dict:
    period_start, period_end = current_period()
    counters = UsageCounter.objects.filter(
        user=user, period_start=period_start
    )
    executions = sum(counter.executions for counter in counters)
    api_calls = sum(counter.api_calls for counter in counters)
    return {
        "period_start": period_start,
        "period_end": period_end,
        "executions": executions,
        "api_calls": api_calls,
    }


def create_checkout_session(user, plan: Plan, success_url: str, cancel_url: str) -> dict:
    if not stripe_configured() or not plan.stripe_price_id:
        return {
            "url": f"{settings.FRONTEND_URL}/billing/mock-checkout?plan={plan.code}",
            "session_id": "",
            "mock": True,
        }

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user.id), "plan_code": plan.code},
        allow_promotion_codes=True,
    )
    return {"url": session.url, "session_id": session.id, "mock": False}


def create_portal_session(user, return_url: str) -> dict:
    if not stripe_configured():
        return {"url": f"{settings.FRONTEND_URL}/billing", "mock": True}
    subscription = (
        Subscription.objects.filter(user=user, external_id__gt="")
        .order_by("-created_at")
        .first()
    )
    if subscription is None:
        return {"url": f"{settings.FRONTEND_URL}/billing", "mock": True}
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.billing_portal.Session.create(
        customer=subscription.external_id,
        return_url=return_url,
    )
    return {"url": session.url, "mock": False}


def _timestamp(value) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)


def handle_checkout_completed(session: dict) -> None:
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan_code = metadata.get("plan_code")
    if not user_id or not plan_code:
        logger.warning("Stripe checkout session without user/plan metadata")
        return
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(id=user_id).first()
    plan = Plan.objects.filter(code=plan_code).first()
    if user is None or plan is None:
        logger.warning("Stripe checkout references unknown user or plan")
        return
    subscription, _ = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "status": Subscription.Status.ACTIVE,
            "external_id": session.get("subscription") or "",
        },
    )
    from .models import Payment

    Payment.objects.get_or_create(
        external_id=session.get("id"),
        defaults={
            "user": user,
            "subscription": subscription,
            "amount": plan.price_monthly,
            "currency": plan.currency,
            "status": Payment.Status.SUCCEEDED,
            "paid_at": datetime.now(tz=dt_timezone.utc),
            "payload": session,
        },
    )


def handle_subscription_deleted(subscription_data: dict) -> None:
    subscription = Subscription.objects.filter(external_id=subscription_data.get("id")).first()
    if subscription:
        subscription.status = Subscription.Status.CANCELED
        subscription.save(update_fields=["status", "updated_at"])


def handle_invoice_paid(invoice_data: dict) -> None:
    from .models import Invoice, Payment

    subscription = Subscription.objects.filter(
        external_id=invoice_data.get("subscription")
    ).first()
    user = subscription.user if subscription else None
    if user is None:
        return
    Invoice.objects.get_or_create(
        external_id=invoice_data.get("id", ""),
        defaults={
            "user": user,
            "subscription": subscription,
            "number": invoice_data.get("number") or invoice_data.get("id", "unknown"),
            "amount": (invoice_data.get("amount_paid") or 0) / 100,
            "currency": (invoice_data.get("currency") or "usd").lower(),
            "status": Invoice.Status.PAID,
            "paid_at": datetime.now(tz=dt_timezone.utc),
            "pdf_url": invoice_data.get("invoice_pdf") or "",
        },
    )
    Payment.objects.get_or_create(
        external_id=invoice_data.get("payment_intent") or invoice_data.get("id"),
        defaults={
            "user": user,
            "subscription": subscription,
            "amount": (invoice_data.get("amount_paid") or 0) / 100,
            "currency": (invoice_data.get("currency") or "usd").lower(),
            "status": Payment.Status.SUCCEEDED,
            "paid_at": datetime.now(tz=dt_timezone.utc),
            "payload": invoice_data,
        },
    )
