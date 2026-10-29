"""Sync the built-in command library from ``content/commands`` into the database."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.commands.models import CommandLibrary
from apps.commands.registry import CommandLibraryRegistry


class Command(BaseCommand):
    help = "Create or update command library entries from the JSON content folder."

    def handle(self, *args: Any, **options: Any) -> None:
        commands = CommandLibraryRegistry.load_commands(force_reload=True)
        if not commands:
            self.stdout.write(self.style.WARNING("No command JSON files found."))
            return

        created = 0
        updated = 0
        with transaction.atomic():
            for slug, data in sorted(commands.items()):
                _, was_created = CommandLibrary.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "category": str(data.get("category", "other")),
                        "title": str(data.get("title") or data.get("name") or slug),
                        "description": str(data.get("description", "")),
                        "type": str(data.get("type", CommandLibrary.Type.SLASH)),
                        "options": list(data.get("options") or []),
                        "flow": data.get("flow") or {},
                        "required_permissions": data.get("required_permissions") or [],
                        "required_intents": list(data.get("required_intents") or []),
                        "dependencies": list(data.get("dependencies") or []),
                        "is_active": True,
                    },
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(
            self.style.SUCCESS(f"Command library: {created} created, {updated} updated.")
        )
