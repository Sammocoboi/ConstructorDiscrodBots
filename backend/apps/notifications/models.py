"""In-app notifications."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class Notification(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "read_at"))]

    def __str__(self) -> str:
        return f"{self.user.email}: {self.type}"
