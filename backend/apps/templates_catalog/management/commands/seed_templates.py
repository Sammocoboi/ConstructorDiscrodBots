"""Load the built-in system templates from ``runtime/content/templates``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.templates_catalog.models import Template, TemplateVersion

TEMPLATE_DIRS = (
    settings.REPO_ROOT / "runtime" / "content" / "templates",
    settings.REPO_ROOT / "content" / "templates",
)


class Command(BaseCommand):
    help = "Create or update system templates from the JSON content folder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            dest="template_dir",
            help="Directory with template JSON files (defaults to runtime/content/templates).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options.get("template_dir"):
            directories = [Path(options["template_dir"])]
        else:
            directories = [path for path in TEMPLATE_DIRS if path.exists()]

        files = sorted(path for directory in directories for path in directory.glob("*.json"))
        if not files:
            self.stdout.write(self.style.WARNING("No template JSON files found."))
            return

        created = 0
        updated = 0
        for path in files:
            data = self._read(path)
            template, was_created = self._upsert(data)
            created += int(was_created)
            updated += int(not was_created)
            self.stdout.write(f"{'created' if was_created else 'updated'}: {template.title}")

        self.stdout.write(self.style.SUCCESS(f"Templates: {created} created, {updated} updated."))

    def _read(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or not data.get("title"):
            raise ValueError(f"{path} is not a valid template: missing title")
        return data

    @transaction.atomic
    def _upsert(self, data: dict[str, Any]) -> tuple[Template, bool]:
        title = str(data["title"]).strip()
        template, created = Template.objects.get_or_create(
            title=title,
            is_system=True,
            defaults={
                "description": str(data.get("description", "")),
                "category": str(data.get("category", "")),
                "visibility": Template.Visibility.PUBLIC,
                "tags": list(data.get("tags") or []),
            },
        )
        if not created:
            template.description = str(data.get("description", template.description))
            template.category = str(data.get("category", template.category))
            template.visibility = Template.Visibility.PUBLIC
            template.tags = list(data.get("tags") or template.tags)
            template.save(
                update_fields=["description", "category", "visibility", "tags", "updated_at"]
            )

        version = str(data.get("version", "1.0.0"))
        TemplateVersion.objects.update_or_create(
            template=template,
            version=version,
            defaults={
                "content": data.get("config") or data.get("content") or {},
                "changelog": str(data.get("description", "")),
            },
        )
        return template, created
