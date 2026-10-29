"""Sync the built-in module manifests into the database."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.modules.models import Module
from apps.modules.registry import ModuleRegistry


class Command(BaseCommand):
    help = "Create or update module catalog entries from the built-in manifests."

    def handle(self, *args: Any, **options: Any) -> None:
        manifests = ModuleRegistry.list_all()
        if not manifests:
            self.stdout.write(self.style.WARNING("No built-in modules found."))
            return

        created = 0
        updated = 0
        with transaction.atomic():
            for manifest in manifests:
                slug = manifest["slug"]
                _, was_created = Module.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "title": str(manifest.get("title", slug)),
                        "description": str(manifest.get("description", "")),
                        "manifest": manifest,
                        "settings_schema": manifest.get("settings_schema") or {},
                        "is_premium": bool(manifest.get("is_premium", False)),
                        "min_plan": str(manifest.get("min_plan", Module.Plan.FREE)),
                        "is_active": True,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"Modules: {created} created, {updated} updated."))
