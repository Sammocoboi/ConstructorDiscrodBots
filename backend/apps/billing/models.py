"""Plans, subscriptions, payments, invoices and usage counters."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class Plan(BaseModel):
    class Code(models.TextChoices):
        FREE = "free", "Free"
        PRO = "pro", "Pro"
        BUSINESS = "business", "Business"

    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=64)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="usd")
    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    limits = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ("sort_order", "price_monthly")

    def __str__(self) -> str:
        return self.name


class Subscription(BaseModel):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Пробный период"
        ACTIVE = "active", "Активна"
        PAST_DUE = "past_due", "Просрочена"
        CANCELED = "canceled", "Отменена"
        EXPIRED = "expired", "Истекла"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    external_id = models.CharField(max_length=100, blank=True, default="")
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    trial_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "status"))]

    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.ACTIVE, self.Status.TRIALING}


class Payment(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        SUCCEEDED = "succeeded", "Успешен"
        FAILED = "failed", "Ошибка"
        REFUNDED = "refunded", "Возврат"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    external_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ("-created_at",)


class Invoice(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        OPEN = "open", "Открыт"
        PAID = "paid", "Оплачен"
        VOID = "void", "Аннулирован"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices"
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    number = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    external_id = models.CharField(max_length=100, blank=True, default="")
    issued_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    pdf_url = models.URLField(blank=True, default="")

    class Meta:
        verbose_name = "Счёт"
        verbose_name_plural = "Счета"
        ordering = ("-issued_at",)


class UsageCounter(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_counters"
    )
    bot = models.ForeignKey(
        "bots.Bot",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="usage_counters",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    executions = models.PositiveIntegerField(default=0)
    api_calls = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Счётчик использования"
        verbose_name_plural = "Счётчики использования"
        ordering = ("-period_start",)
        indexes = [models.Index(fields=("user", "period_start"))]
