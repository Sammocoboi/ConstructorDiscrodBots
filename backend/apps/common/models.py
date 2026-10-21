"""Base abstract models used across the project."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from .utils import uuid7


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):  # type: ignore[override]
        return self.update(deleted_at=timezone.now())


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    pass


class SoftDeleteModel(BaseModel):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):  # type: ignore[override]
        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=["deleted_at", "updated_at"])


class IdempotencyKey(BaseModel):
    """Сохранённый ответ на запрос с заголовком Idempotency-Key."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )
    key = models.CharField(max_length=255)
    request_method = models.CharField(max_length=10)
    request_path = models.CharField(max_length=500)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = "Ключ идемпотентности"
        verbose_name_plural = "Ключи идемпотентности"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "key"), name="unique_user_idempotency_key")
        ]
        indexes = [models.Index(fields=("expires_at",))]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.key}"
