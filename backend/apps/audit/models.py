"""Audit log for sensitive actions."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class AuditLog(BaseModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100, db_index=True)
    object_type = models.CharField(max_length=100, blank=True, default="")
    object_id = models.CharField(max_length=100, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    diff = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("object_type", "object_id"))]

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"

    @classmethod
    def record(cls, *, actor=None, action: str, obj=None, request=None, diff=None):
        return cls.objects.create(
            actor=actor,
            action=action,
            object_type=obj.__class__.__name__ if obj is not None else "",
            object_id=str(getattr(obj, "id", "")) if obj is not None else "",
            ip=(
                request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR")
                if request
                else None
            ),
            user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
            diff=diff or {},
        )
