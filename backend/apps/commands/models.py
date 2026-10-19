"""Ready-made command library."""

from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel


class CommandLibrary(SoftDeleteModel):
    class Type(models.TextChoices):
        SLASH = "slash", "Slash-команда"
        PREFIX = "prefix", "Префиксная команда"
        CONTEXT_MENU = "context_menu", "Контекстное меню"

    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SLASH)
    options = models.JSONField(default=list, blank=True)
    flow = models.JSONField(default=dict, blank=True)
    required_permissions = models.JSONField(default=list, blank=True)
    required_intents = models.JSONField(default=list, blank=True)
    dependencies = models.JSONField(default=list, blank=True)
    popularity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Команда библиотеки"
        verbose_name_plural = "Библиотека команд"
        ordering = ("category", "title")
        indexes = [models.Index(fields=("category", "is_active"))]

    def __str__(self) -> str:
        return f"/{self.slug}"
