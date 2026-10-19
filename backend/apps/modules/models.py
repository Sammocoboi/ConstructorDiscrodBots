"""Module manifests and settings JSON Schema."""

from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel


class Module(SoftDeleteModel):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        PRO = "pro", "Pro"
        BUSINESS = "business", "Business"

    slug = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    manifest = models.JSONField(
        default=dict,
        blank=True,
        help_text="Команды, события, права, intents модуля",
    )
    settings_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON Schema настроек, из которого генерируется UI",
    )
    is_premium = models.BooleanField(default=False)
    min_plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Модуль"
        verbose_name_plural = "Модули"
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title
