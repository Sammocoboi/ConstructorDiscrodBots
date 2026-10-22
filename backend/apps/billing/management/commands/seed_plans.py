"""Seed the three plans from the technical specification."""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.billing.models import Plan

PLANS = [
    {
        "code": Plan.Code.FREE,
        "name": "Free",
        "price_monthly": 0,
        "limits": {
            "bots": 1,
            "guilds_per_bot": 3,
            "scenarios": 20,
            "blocks_per_scenario": 50,
            "executions_per_month": 10_000,
            "premium_modules": False,
            "priority_support": False,
        },
        "sort_order": 1,
    },
    {
        "code": Plan.Code.PRO,
        "name": "Pro",
        "price_monthly": 19,
        "limits": {
            "bots": 5,
            "guilds_per_bot": 50,
            "scenarios": 200,
            "blocks_per_scenario": 300,
            "executions_per_month": 500_000,
            "premium_modules": True,
            "priority_support": False,
        },
        "stripe_price_id": settings.STRIPE_PRICE_PRO,
        "sort_order": 2,
    },
    {
        "code": Plan.Code.BUSINESS,
        "name": "Business",
        "price_monthly": 99,
        "limits": {
            "bots": 20,
            "guilds_per_bot": 0,
            "guilds_per_bot_note": "без ограничения (fair use)",
            "scenarios": 1000,
            "blocks_per_scenario": 1000,
            "executions_per_month": 5_000_000,
            "premium_modules": True,
            "priority_support": True,
        },
        "stripe_price_id": settings.STRIPE_PRICE_BUSINESS,
        "sort_order": 3,
    },
]


class Command(BaseCommand):
    help = "Create or update Free/Pro/Business plans"

    def handle(self, *args, **options):
        for data in PLANS:
            plan, created = Plan.objects.update_or_create(
                code=data["code"],
                defaults={**data, "currency": "usd", "is_active": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"{plan.code}: {action}"))
