"""Billing API and Stripe webhook."""

from __future__ import annotations

import json
import logging
from typing import cast

import stripe
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from . import services
from .models import Invoice, Plan, Subscription
from .serializers import (
    CheckoutSerializer,
    InvoiceSerializer,
    PlanSerializer,
    PortalSerializer,
    SubscriptionSerializer,
    UsageSerializer,
)

logger = logging.getLogger(__name__)


class PlanListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    serializer_class = PlanSerializer
    queryset = Plan.objects.filter(is_active=True)
    pagination_class = None


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SubscriptionSerializer}, summary="Текущая подписка")
    def get(self, request):
        subscription = (
            Subscription.objects.filter(user=request.user)
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )
        return Response(SubscriptionSerializer(subscription).data if subscription else None)


class UsageView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UsageSerializer}, summary="Использование лимитов тарифа")
    def get(self, request):
        plan = services.get_active_plan(request.user)
        usage = services.get_usage(request.user)
        limits = plan.limits if plan else {}
        return Response(
            {
                **usage,
                "limits": limits,
                "plan": PlanSerializer(plan).data if plan else None,
            }
        )


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CheckoutSerializer,
        responses={200: OpenApiResponse(description="Checkout URL")},
        summary="Создать Stripe Checkout",
    )
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = Plan.objects.filter(
            code=serializer.validated_data["plan_code"], is_active=True
        ).first()
        if plan is None:
            raise NotFound("Plan not found")
        success_url = serializer.validated_data.get(
            "success_url", f"{settings.FRONTEND_URL}/billing?status=success"
        )
        cancel_url = serializer.validated_data.get(
            "cancel_url", f"{settings.FRONTEND_URL}/billing?status=cancel"
        )
        return Response(
            services.create_checkout_session(request.user, plan, success_url, cancel_url)
        )


class PortalView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PortalSerializer,
        responses={200: OpenApiResponse(description="Portal URL")},
        summary="Stripe Billing Portal",
    )
    def post(self, request):
        serializer = PortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return_url = serializer.validated_data.get("return_url", f"{settings.FRONTEND_URL}/billing")
        return Response(services.create_portal_session(request.user, return_url))


class InvoiceListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Invoice.objects.none()
        return Invoice.objects.filter(user=cast(User, self.request.user))


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description="Webhook processed")},
        summary="Stripe webhook",
    )
    def post(self, request):
        payload = request.body
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        if settings.STRIPE_WEBHOOK_SECRET and settings.STRIPE_SECRET_KEY:
            try:
                event = stripe.Webhook.construct_event(
                    payload, signature, settings.STRIPE_WEBHOOK_SECRET
                )
            except (ValueError, stripe.SignatureVerificationError) as exc:
                logger.warning("Rejected Stripe webhook with invalid signature")
                raise ValidationError({"detail": "Invalid signature"}) from exc
        else:
            try:
                event = json.loads(payload or b"{}")
            except json.JSONDecodeError as exc:
                raise ValidationError({"detail": "Invalid JSON"}) from exc
            logger.warning("Stripe webhook signature is not configured; accepting unsigned event")

        event_type = event.get("type", "")
        data = (event.get("data") or {}).get("object") or {}

        if event_type == "checkout.session.completed":
            services.handle_checkout_completed(data)
        elif event_type == "customer.subscription.deleted":
            services.handle_subscription_deleted(data)
        elif event_type == "invoice.paid":
            services.handle_invoice_paid(data)
        else:
            logger.info("Unhandled Stripe event: %s", event_type)

        return Response({"received": True})
