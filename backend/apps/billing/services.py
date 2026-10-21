"""Billing business logic and Stripe integration."""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import UTC, date, datetime

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import LimitExceeded
from apps.notifications.models import Notification

from .models import Plan, Subscription, UsageCounter

logger = logging.getLogger(__name__)

LIMIT_WARNING_THRESHOLD = 0.8


def stripe_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def current_period() -> tuple[date, date]:
    today = date.today()
    last_day = monthrange(today.year, today.month)[1]
    return date(today.year, today.month, 1), date(today.year, today.month, last_day)


def get_active_plan(user) -> Plan | None:
    subscription = (
        Subscription.objects.filter(
            user=user,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING],
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    if subscription is not None:
        period_end = subscription.current_period_end
        if period_end is not None and period_end <= timezone.now():
            # Подписка истекла — деградируем до Free (FR-4.10).
            subscription.status = Subscription.Status.EXPIRED
            subscription.save(update_fields=["status", "updated_at"])
        elif subscription.plan.is_active:
            return subscription.plan
    return Plan.objects.filter(code=Plan.Code.FREE, is_active=True).first()


def plan_limits(plan: Plan | None) -> dict:
    if plan is None or not isinstance(plan.limits, dict):
        return {}
    return plan.limits


def _limit_value(limits: dict, name: str) -> int | None:
    value = limits.get(name)
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        logger.warning("Invalid limit %s=%r, ignoring", name, value)
        return None


def limit_percent(used: int, limit: int | None) -> int:
    if limit is None:
        return 0
    if limit <= 0:
        return 100
    return min(100, round(used * 100 / limit))


def get_usage(user) -> dict:
    period_start, period_end = current_period()
    counters = UsageCounter.objects.filter(user=user, period_start=period_start)
    executions = sum(counter.executions for counter in counters)
    api_calls = sum(counter.api_calls for counter in counters)
    return {
        "period_start": period_start,
        "period_end": period_end,
        "executions": executions,
        "api_calls": api_calls,
    }


def get_usage_summary(user) -> dict:
    """План, лимиты, использование и проценты для UI и проверок."""
    plan = get_active_plan(user)
    limits = plan_limits(plan)
    usage = get_usage(user)
    bots_used = user.bots.count()
    executions_limit = _limit_value(limits, "executions_per_month")
    bots_limit = _limit_value(limits, "bots")

    warnings = []
    if (
        executions_limit is not None
        and usage["executions"] >= LIMIT_WARNING_THRESHOLD * executions_limit
    ):
        warnings.append("executions_per_month")
    if bots_limit is not None and bots_used >= LIMIT_WARNING_THRESHOLD * bots_limit:
        warnings.append("bots")

    return {
        **usage,
        "plan": plan,
        "limits": limits,
        "bots_used": bots_used,
        "bots_limit": bots_limit,
        "executions_limit": executions_limit,
        "bots_percent": limit_percent(bots_used, bots_limit),
        "executions_percent": limit_percent(usage["executions"], executions_limit),
        "execution_blocked": (
            executions_limit is not None and usage["executions"] >= executions_limit
        ),
        "warnings": warnings,
    }


def ensure_bot_limit(user) -> None:
    """Не даёт создать бота сверх лимита тарифа."""
    plan = get_active_plan(user)
    limits = plan_limits(plan)
    limit = _limit_value(limits, "bots")
    if limit is None:
        return
    used = user.bots.count()
    if used >= limit:
        plan_name = plan.name if plan else "Free"
        raise LimitExceeded(
            "bots",
            f"На тарифе {plan_name} доступно не больше {limit} ботов",
        )


def check_execution_limit(user) -> dict:
    """Проверка перед запуском сценария Runtime-ом. 100% — блокировка."""
    summary = get_usage_summary(user)
    limit = summary["executions_limit"]
    if limit is not None and summary["executions"] >= limit:
        raise LimitExceeded(
            "executions_per_month",
            f"Лимит выполнений на текущий месяц исчерпан ({limit})",
        )
    return summary


def _notify_limit_warning(user, kind: str, used: int, limit: int, period_start: date) -> None:
    if limit <= 0:
        return
    notification_type = f"limit_warning_{kind}"
    already_sent = Notification.objects.filter(
        user=user,
        type=notification_type,
        created_at__date__gte=period_start,
    ).exists()
    if already_sent:
        return
    Notification.objects.create(
        user=user,
        type=notification_type,
        payload={
            "kind": kind,
            "used": used,
            "limit": limit,
            "percent": limit_percent(used, limit),
        },
    )


def record_usage(
    user,
    *,
    executions: int = 0,
    api_calls: int = 0,
    bot=None,
) -> UsageCounter:
    """Атомарно увеличивает счётчики и создаёт предупреждение на 80%."""
    period_start, period_end = current_period()
    with transaction.atomic():
        counter, _ = UsageCounter.objects.get_or_create(
            user=user,
            bot=bot,
            period_start=period_start,
            defaults={"period_end": period_end},
        )
        counter = UsageCounter.objects.select_for_update().get(pk=counter.pk)
        counter.executions += max(0, executions)
        counter.api_calls += max(0, api_calls)
        counter.save(update_fields=["executions", "api_calls", "updated_at"])

    totals = get_usage(user)
    plan = get_active_plan(user)
    limits = plan_limits(plan)

    if executions:
        limit = _limit_value(limits, "executions_per_month")
        if limit is not None and totals["executions"] >= LIMIT_WARNING_THRESHOLD * limit:
            _notify_limit_warning(
                user, "executions_per_month", totals["executions"], limit, period_start
            )
    if api_calls:
        limit = _limit_value(limits, "api_calls_per_month")
        if limit is not None and totals["api_calls"] >= LIMIT_WARNING_THRESHOLD * limit:
            _notify_limit_warning(
                user, "api_calls_per_month", totals["api_calls"], limit, period_start
            )
    return counter


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
        Subscription.objects.filter(user=user, external_id__gt="").order_by("-created_at").first()
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
    return datetime.fromtimestamp(int(value), tz=UTC)


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
            "paid_at": datetime.now(tz=UTC),
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

    subscription = Subscription.objects.filter(external_id=invoice_data.get("subscription")).first()
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
            "paid_at": datetime.now(tz=UTC),
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
            "paid_at": datetime.now(tz=UTC),
            "payload": invoice_data,
        },
    )
