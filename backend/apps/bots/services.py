
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from backend.apps.bots.models import Bot, BotGuild, BotStatus, DesiredState
from backend.apps.notifications.services import NotificationService
from backend.integrations.discord.client import (
    DiscordRestClient,
    DiscordUnauthorizedError,
    DiscordAPIError,
)
from backend.integrations.discord.permissions import (
    calculate_permissions_integer,
    calculate_required_intents,
    generate_invite_url,
)

logger = logging.getLogger(__name__)

PLAN_BOT_LIMITS = {
    "free": 1,
    "pro": 5,
    "business": 20,
}

class BotService:
    @staticmethod
    def check_bot_limit(owner_id: str, plan_name: str = "free") -> None:
        limit = PLAN_BOT_LIMITS.get(plan_name.lower(), 1)
        active_count = Bot.objects.filter(owner_id=owner_id, deleted_at__isnull=True).count()
        if active_count >= limit:
            raise PermissionDenied(
                f"Превышен лимит ботов для тарифа «{plan_name.upper()}» ({limit} шт.). "
                f"Повысьте тариф до Pro или Business для добавления новых ботов."
            )

    @staticmethod
    def validate_discord_token(plain_token: str) -> Dict[str, Any]:
        if not plain_token or len(plain_token.strip()) < 20:
            raise ValidationError("Токен бота имеет некорректный формат")

        client = DiscordRestClient(bot_token=plain_token.strip())
        try:
            bot_data = client.get_current_bot_user()
        except DiscordUnauthorizedError:
            raise ValidationError("Discord вернул 401 Unauthorized: указан недействительный токен бота")
        except DiscordAPIError as e:
            raise ValidationError(f"Ошибка проверки токена в Discord API: {e.message}")

        avatar_hash = bot_data.get("avatar")
        user_id = bot_data.get("id")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
            if avatar_hash
            else "https://cdn.discordapp.com/embed/avatars/0.png"
        )

        return {
            "id": user_id,
            "username": bot_data.get("username"),
            "discriminator": bot_data.get("discriminator", "0"),
            "avatar_url": avatar_url,
            "bot": True,
            "flags": bot_data.get("flags", 0),
        }

    @staticmethod
    def update_bot_token(bot: Bot, new_plain_token: str, user_email: Optional[str] = None) -> Bot:
        validated = BotService.validate_discord_token(new_plain_token)
        bot.set_token(new_plain_token.strip())
        bot.discord_application_id = validated["id"]
        bot.discord_bot_user_id = validated["id"]
        bot.name = validated["username"]
        bot.avatar_url = validated["avatar_url"]
        bot.discriminator = validated["discriminator"]
        bot.last_error = None
        bot.last_error_at = None
        if bot.status == BotStatus.ERROR:
            bot.status = BotStatus.STOPPED
        bot.save()
        return bot

    @staticmethod
    def handle_unauthorized_token(bot: Bot, user_email: Optional[str] = None) -> None:
        logger.warning("Остановка бота %s (%s) из-за Discord 401 Unauthorized", bot.name, bot.id)
        bot.status = BotStatus.ERROR
        bot.desired_state = DesiredState.STOPPED
        bot.last_error = "Discord 401 Unauthorized: Токен бота недействителен или был сброшен в Discord Developer Portal."
        bot.last_error_at = timezone.now()
        bot.save()

        target_email = user_email or f"{bot.owner_id}@example.com"
        NotificationService.send_bot_token_invalid_alert(
            to_email=target_email,
            user_name="Пользователь",
            bot_name=bot.name,
            bot_id=str(bot.id),
            error_details=bot.last_error
        )

    @staticmethod
    def get_bot_client(bot: Bot, user_email: Optional[str] = None) -> DiscordRestClient:
        plain_token = bot.get_token()
        if not plain_token:
            raise ValidationError("У бота не задан токен авторизации Discord")

        def on_401():
            BotService.handle_unauthorized_token(bot, user_email)

        return DiscordRestClient(bot_token=plain_token, on_unauthorized_callback=on_401)

    @staticmethod
    def get_invite_url(bot: Bot, guild_id: Optional[str] = None) -> Dict[str, Any]:
        client_id = bot.discord_application_id or str(bot.id)
        
        enabled_modules: set = set()
        for guild in bot.guilds.all():
            enabled_modules.update(guild.enabled_modules or [])
        
        if not enabled_modules:
            enabled_modules = {"core", "welcomes", "moderation"}

        perms_int = calculate_permissions_integer(list(enabled_modules))
        required_intents = calculate_required_intents(list(enabled_modules))
        invite_url = generate_invite_url(client_id=client_id, permissions_integer=perms_int, guild_id=guild_id)

        return {
            "bot_id": str(bot.id),
            "client_id": client_id,
            "permissions_integer": perms_int,
            "required_intents": required_intents,
            "invite_url": invite_url,
            "enabled_modules": list(enabled_modules),
        }

    @staticmethod
    def sync_slash_commands(
        bot: Bot,
        commands_list: List[Dict[str, Any]],
        test_guild_id: Optional[str] = None,
        force: bool = False,
        user_email: Optional[str] = None
    ) -> Dict[str, Any]:
        if not bot.discord_application_id:
            raise ValidationError("У бота отсутствует discord_application_id. Сначала подключите токен бота.")

        dumped = json.dumps(commands_list, sort_keys=True, ensure_ascii=False)
        current_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()

        if current_hash == bot.commands_hash and not force and not test_guild_id:
            return {
                "status": "skipped",
                "message": "Набор команд не изменился (хеш совпадает). Синхронизация пропущена.",
                "hash": current_hash,
                "commands_count": len(commands_list),
            }

        client = BotService.get_bot_client(bot, user_email)

        if test_guild_id:
            registered = client.bulk_overwrite_guild_commands(
                application_id=bot.discord_application_id,
                guild_id=test_guild_id,
                commands=commands_list
            )
            mode = f"guild:{test_guild_id}"
        else:
            registered = client.bulk_overwrite_global_commands(
                application_id=bot.discord_application_id,
                commands=commands_list
            )
            mode = "global"
            bot.commands_hash = current_hash
            bot.save(update_fields=["commands_hash"])

        return {
            "status": "synchronized",
            "mode": mode,
            "registered_count": len(registered) if isinstance(registered, list) else len(commands_list),
            "hash": current_hash,
        }
