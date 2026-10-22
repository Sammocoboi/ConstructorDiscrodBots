"""Templates and immutable template versions."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, SoftDeleteModel


class Template(SoftDeleteModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Приватный"
        UNLISTED = "unlisted", "По ссылке"
        PUBLIC = "public", "Публичный"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="templates",
        help_text="Пусто для системного шаблона",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=64, blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    tags = models.JSONField(default=list, blank=True)
    is_system = models.BooleanField(default=False)
    popularity = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Шаблон"
        verbose_name_plural = "Шаблоны"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("category", "visibility")),
            models.Index(fields=("is_system",)),
        ]

    def __str__(self) -> str:
        return self.title


class TemplateVersion(BaseModel):
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=32, default="1.0.0")
    changelog = models.TextField(blank=True, default="")
    content = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Версия шаблона"
        verbose_name_plural = "Версии шаблонов"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("template", "version"), name="unique_template_version")
        ]

    def __str__(self) -> str:
        return f"{self.template.title} v{self.version}"
