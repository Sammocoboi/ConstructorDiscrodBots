"""Bot projects, guilds, versions, runtime commands and runtime state."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import BaseModel, SoftDeleteModel


def bot_avatar_path(instance: Bot, filename: str) -> str:
    return f"bots/{instance.id}/avatar-{uuid.uuid4().hex}.png"


def bot_banner_path(instance: Bot, filename: str) -> str:
    return f"bots/{instance.id}/banner-{uuid.uuid4().hex}.png"


class BotStatus(models.TextChoices):
    STOPPED = "stopped", "Остановлен"
    STARTING = "starting", "Запускается"
    ONLINE = "online", "Онлайн"
    ERROR = "error", "Ошибка"
    SUSPENDED = "suspended", "Приостановлен"


class DesiredState(models.TextChoices):
    RUNNING = "running", "Должен работать"
    STOPPED = "stopped", "Должен быть остановлен"


class Bot(SoftDeleteModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Приватный"
        PUBLIC = "public", "Публичный"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bots"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True, null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE
    )
    avatar = models.ImageField(upload_to=bot_avatar_path, blank=True)
    banner = models.ImageField(upload_to=bot_banner_path, blank=True)
    discord_application_id = models.CharField(max_length=32, blank=True, default="")
    discord_bot_user_id = models.CharField(max_length=32, blank=True, default="")
    token_encrypted = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=BotStatus.choices, default=BotStatus.STOPPED)
    desired_state = models.CharField(
        max_length=20, choices=DesiredState.choices, default=DesiredState.STOPPED
    )
    active_version = models.ForeignKey(
        "bots.BotVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    profile = models.JSONField(default=dict, blank=True)
    intents = models.JSONField(default=list, blank=True)
    last_error = models.TextField(blank=True, default="")
    last_error_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Бот"
        verbose_name_plural = "Боты"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("owner", "status")),
            models.Index(fields=("desired_state",)),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True)[:100] or "bot"
            suffix = self.id.hex[-8:] if self.id else uuid.uuid4().hex[:8]
            self.slug = f"{base}-{suffix}"
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = [*update_fields, "slug"]
        return super().save(*args, **kwargs)

    @property
    def has_token(self) -> bool:
        return bool(self.token_encrypted)

    @property
    def is_public(self) -> bool:
        return self.visibility == self.Visibility.PUBLIC


class BotMember(BaseModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Владелец"
        EDITOR = "editor", "Редактор"
        VIEWER = "viewer", "Наблюдатель"

    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bot_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)

    class Meta:
        verbose_name = "Участник проекта"
        verbose_name_plural = "Участники проектов"
        constraints = [models.UniqueConstraint(fields=("bot", "user"), name="unique_bot_member")]


class BotGuild(SoftDeleteModel):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="guilds")
    guild_id = models.CharField(max_length=32)
    guild_name = models.CharField(max_length=100, blank=True, default="")
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    enabled_modules = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "Гильдия бота"
        verbose_name_plural = "Гильдии ботов"
        constraints = [models.UniqueConstraint(fields=("bot", "guild_id"), name="unique_bot_guild")]
        ordering = ("guild_name",)

    def __str__(self) -> str:
        return f"{self.guild_name or self.guild_id} ({self.bot.name})"


class BotDraft(BaseModel):
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="draft")
    content = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "Черновик бота"
        verbose_name_plural = "Черновики ботов"


class BotVersion(BaseModel):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    content = models.JSONField(default=dict, blank=True)
    comment = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Версия бота"
        verbose_name_plural = "Версии ботов"
        ordering = ("-version_number",)
        constraints = [
            models.UniqueConstraint(fields=("bot", "version_number"), name="unique_bot_version")
        ]

    def __str__(self) -> str:
        return f"{self.bot.name} v{self.version_number}"


class BotVariable(BaseModel):
    class Scope(models.TextChoices):
        USER = "user", "Пользователь"
        GUILD = "guild", "Гильдия"
        GLOBAL = "global", "Глобально"

    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="variables")
    scope = models.CharField(max_length=20, choices=Scope.choices)
    guild_id = models.CharField(max_length=32, blank=True, default="")
    user_discord_id = models.CharField(max_length=32, blank=True, default="")
    key = models.CharField(max_length=100)
    value = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Переменная бота"
        verbose_name_plural = "Переменные ботов"
        constraints = [
            models.UniqueConstraint(
                fields=("bot", "scope", "guild_id", "user_discord_id", "key"),
                name="unique_bot_variable",
            )
        ]
        indexes = [models.Index(fields=("bot", "scope", "key"))]


class RuntimeCommand(BaseModel):
    class Command(models.TextChoices):
        START = "start", "Запуск"
        STOP = "stop", "Остановка"
        RESTART = "restart", "Перезапуск"
        RELOAD = "reload", "Горячая замена конфигурации"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        ACKNOWLEDGED = "acknowledged", "Подтверждена"
        FAILED = "failed", "Ошибка"

    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="runtime_commands")
    command = models.CharField(max_length=20, choices=Command.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Команда Runtime"
        verbose_name_plural = "Команды Runtime"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("bot", "status"))]


class BotRuntimeState(BaseModel):
    bot = models.OneToOneField(Bot, on_delete=models.CASCADE, related_name="runtime_state")
    worker_id = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=BotStatus.choices, default=BotStatus.STOPPED)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    guild_count = models.PositiveIntegerField(default=0)
    uptime_seconds = models.PositiveIntegerField(default=0)
    version_number = models.PositiveIntegerField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Состояние бота"
        verbose_name_plural = "Состояния ботов"

    @property
    def is_alive(self) -> bool:
        if self.heartbeat_at is None:
            return False
        return (timezone.now() - self.heartbeat_at).total_seconds() <= 60


class ScheduledJob(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        RUNNING = "running", "Выполняется"
        DONE = "done", "Выполнена"
        FAILED = "failed", "Ошибка"

    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="scheduled_jobs")
    guild_id = models.CharField(max_length=32, blank=True, default="")
    flow_id = models.CharField(max_length=64)
    run_at = models.DateTimeField()
    cron = models.CharField(max_length=100, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        verbose_name = "Отложенная задача"
        verbose_name_plural = "Отложенные задачи"
        ordering = ("run_at",)
        indexes = [models.Index(fields=("status", "run_at"))]
