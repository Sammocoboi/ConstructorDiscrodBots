"""User, OAuth accounts and refresh sessions."""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import AllObjectsManager, SoftDeleteManager, SoftDeleteModel


class UserManager(SoftDeleteManager, BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=150)
    avatar_url = models.URLField(blank=True, default="")
    locale = models.CharField(
        max_length=10,
        choices=[("ru", "Русский"), ("en", "English")],
        default="ru",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()  # type: ignore[misc]
    all_objects = AllObjectsManager()  # type: ignore[misc]

    USERNAME_FIELD = "email"  # type: ignore[misc]
    REQUIRED_FIELDS: list[str] = []  # type: ignore[misc]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.email

    @property
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None

    def mark_email_verified(self) -> None:
        if self.email_verified_at is None:
            self.email_verified_at = timezone.now()
            self.save(update_fields=["email_verified_at", "updated_at"])


class OAuthAccount(SoftDeleteModel):
    class Provider(models.TextChoices):
        DISCORD = "discord", "Discord"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth_accounts")
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.DISCORD)
    provider_user_id = models.CharField(max_length=64)
    access_token_encrypted = models.TextField(blank=True, default="")
    refresh_token_encrypted = models.TextField(blank=True, default="")
    scopes = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "OAuth-аккаунт"
        verbose_name_plural = "OAuth-аккаунты"
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "provider_user_id"),
                name="unique_oauth_provider_user",
            )
        ]
        indexes = [models.Index(fields=("user", "provider"))]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_user_id}"


class RefreshSession(SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_sessions")
    jti = models.CharField(max_length=255, unique=True)
    token_hash = models.CharField(max_length=64)
    device_info = models.CharField(max_length=255, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Сессия"
        verbose_name_plural = "Сессии"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "revoked_at")),
            models.Index(fields=("expires_at",)),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.jti}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()
