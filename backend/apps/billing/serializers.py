"""Billing serializers."""

from __future__ import annotations

from rest_framework import serializers

from .models import Invoice, Plan, Subscription, UsageCounter


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "code",
            "name",
            "price_monthly",
            "currency",
            "limits",
            "sort_order",
        )
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "trial_end",
            "created_at",
        )
        read_only_fields = fields


class UsageSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    executions = serializers.IntegerField()
    api_calls = serializers.IntegerField()
    limits = serializers.DictField()
    plan = PlanSerializer(allow_null=True)
    bots_used = serializers.IntegerField()
    bots_limit = serializers.IntegerField(allow_null=True)
    executions_limit = serializers.IntegerField(allow_null=True)
    bots_percent = serializers.IntegerField()
    executions_percent = serializers.IntegerField()
    execution_blocked = serializers.BooleanField()
    warnings = serializers.ListField(child=serializers.CharField())


class CheckoutSerializer(serializers.Serializer):
    plan_code = serializers.ChoiceField(choices=Plan.Code.choices)
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)


class PortalSerializer(serializers.Serializer):
    return_url = serializers.URLField(required=False)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "number",
            "amount",
            "currency",
            "status",
            "issued_at",
            "paid_at",
            "pdf_url",
        )
        read_only_fields = fields


class UsageCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageCounter
        fields = ("id", "period_start", "period_end", "executions", "api_calls")
        read_only_fields = fields
