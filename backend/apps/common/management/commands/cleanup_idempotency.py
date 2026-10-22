"""Удаление просроченных ключей идемпотентности."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.models import IdempotencyKey


class Command(BaseCommand):
    help = "Delete expired Idempotency-Key records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Maximum number of records to delete (default: 5000)",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        queryset = IdempotencyKey.objects.filter(expires_at__lte=timezone.now())
        ids = list(queryset.values_list("id", flat=True)[:batch_size])
        deleted, _ = IdempotencyKey.objects.filter(id__in=ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired idempotency keys"))
