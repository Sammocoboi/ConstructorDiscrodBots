"""Экспорт OpenAPI-схемы в docs/openapi.yaml."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import OpenApiYamlRenderer


class Command(BaseCommand):
    help = "Generate docs/openapi.yaml from the current API schema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(settings.REPO_ROOT / "docs" / "openapi.yaml"),
            help="Output file path",
        )

    def handle(self, *args, **options):
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        content = OpenApiYamlRenderer().render(schema, renderer_context={})

        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        self.stdout.write(self.style.SUCCESS(f"OpenAPI schema written to {output}"))
