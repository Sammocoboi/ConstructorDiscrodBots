"""
Модели для управления ботами и гильдиями.
Соответствие ТЗ §7.2 (таблицы bots, bot_guilds) и задачам SAN-1, SAN-3.
"""

import uuid
from django.db import models
from django.utils import timezone
from backend.integrations.discord.crypto import default_cipher


class BotStatus(models.TextChoices):
    STOPPED = "stopped", "Остановлен"
    STARTING = "starting", "Запускается"
    ONLINE = "online", "В сети"
    ERROR = "error", "Ошибка"
    SUSPENDED = "suspended", "Приостановлен"


class DesiredState(models.TextChoices):
    RUNNING = "running", "Работает"
    STOPPED = "stopped", "Остановлен"


class Bot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # В рамках ТЗ id владельца
    owner_id = models.CharField(max_length=64, default="default-user", db_index=True)
    name = models.CharField(max_length=100, default="Новый бот")
    discord_application_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    discord_bot_user_id = models.CharField(max_length=64, blank=True, null=True)
    avatar_url = models.URLField(max_length=500, blank=True, null=True)
    discriminator = models.CharField(max_length=10, blank=True, default="0")
    
    # Зашифрованный токен (AES-256-GCM)
    token_encrypted = models.TextField(blank=True, default="")
    
    status = models.CharField(max_length=20, choices=BotStatus.choices, default=BotStatus.STOPPED)
    desired_state = models.CharField(max_length=20, choices=DesiredState.choices, default=DesiredState.STOPPED)
    
    last_error = models.TextField(blank=True, null=True)
    last_error_at = models.DateTimeField(blank=True, null=True)
    
    # Профиль бота (статус, активность, баннер)
    profile = models.JSONField(default=dict)
    
    # Список включенных Privileged Intents
    intents = models.JSONField(default=list)
    
    # Хеш опубликованных команд для предотвращения лишних запросов к Discord API (FR-4.5)
    commands_hash = models.CharField(max_length=64, blank=True, default="")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "bots"
        ordering = ["-created_at"]

    def set_token(self, plain_token: str) -> None:
        """Шифрует и сохраняет токен бота."""
        if not plain_token:
            self.token_encrypted = ""
        else:
            self.token_encrypted = default_cipher.encrypt(plain_token)

    def get_token(self) -> str:
        """Расшифровывает токен бота для внутренних обращений."""
        if not self.token_encrypted:
            return ""
        return default_cipher.decrypt(self.token_encrypted)

    @property
    def token_masked(self) -> str:
        """Возвращает безопасную маску токена для API и UI."""
        raw = self.get_token()
        return default_cipher.mask_token(raw)


class BotGuild(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE, related_name="guilds")
    guild_id = models.CharField(max_length=64, db_index=True)
    guild_name = models.CharField(max_length=150, default="Discord Server")
    icon_url = models.URLField(max_length=500, blank=True, null=True)
    
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(blank=True, null=True)
    
    # Настройки модулей по гильдии: { "welcomes": {...}, "moderation": {...} }
    settings = models.JSONField(default=dict)
    
    # Список ID включенных модулей на этой гильдии
    enabled_modules = models.JSONField(default=list)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bot_guilds"
        unique_together = ("bot", "guild_id")
        ordering = ["guild_name"]
