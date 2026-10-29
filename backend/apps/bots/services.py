"""Discord and bot lifecycle helpers used by the API layer."""

from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.utils import timezone

from apps.common.crypto import encrypt_secret

from .models import Bot, BotGuild, DesiredState, RuntimeCommand

logger = logging.getLogger(__name__)


class DiscordAPIError(Exception):
    """Raised when Discord rejects a bot token or is unavailable."""


def validate_bot_token(token: str) -> dict:
    if not token:
        raise DiscordAPIError("Bot token is empty")
    try:
        response = requests.get(
            f"{settings.DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise DiscordAPIError("Discord API is unavailable") from exc
    if response.status_code == 401:
        raise DiscordAPIError("Discord rejected the bot token")
    if response.status_code >= 400:
        raise DiscordAPIError(f"Discord API returned {response.status_code}")
    payload = response.json()
    if not payload.get("bot", False):
        raise DiscordAPIError("Token belongs to a user account, not to a bot")
    return payload


def _bot_get(token: str, path: str):
    try:
        response = requests.get(
            f"{settings.DISCORD_API_BASE}{path}",
            headers={"Authorization": f"Bot {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise DiscordAPIError("Discord API is unavailable") from exc
    if response.status_code == 401:
        raise DiscordAPIError("Discord rejected the bot token")
    if response.status_code >= 400:
        raise DiscordAPIError(f"Discord API returned {response.status_code}")
    return response.json()


def fetch_bot_application(token: str) -> dict:
    """Return the Discord application that owns the bot token."""
    return _bot_get(token, "/applications/@me")


def fetch_bot_guilds(token: str) -> list[dict]:
    """Return guilds the bot is currently a member of."""
    payload = _bot_get(token, "/users/@me/guilds")
    return payload if isinstance(payload, list) else []


def inspect_bot_token(token: str) -> dict:
    """Validate a bot token and collect the data needed by the UI.

    ``/applications/@me`` and ``/users/@me/guilds`` are best-effort: a valid
    token must not be rejected only because those endpoints are temporarily
    unavailable or rate-limited.
    """
    user = validate_bot_token(token)
    try:
        application = fetch_bot_application(token)
    except DiscordAPIError:
        logger.warning("Could not fetch Discord application for bot token", exc_info=True)
        application = {}
    try:
        guilds = fetch_bot_guilds(token)
    except DiscordAPIError:
        logger.warning("Could not fetch Discord guilds for bot token", exc_info=True)
        guilds = []
    return {"user": user, "application": application, "guilds": guilds}


def encrypt_bot_token(token: str) -> str:
    return encrypt_secret(token)


def build_invite_url(application_id: str, permissions: int = 0) -> str:
    if not application_id:
        raise DiscordAPIError("Discord application id is required")
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={application_id}&permissions={permissions}&scope=bot%20applications.commands"
    )


def enqueue_runtime_command(
    bot: Bot,
    command: str,
    requested_by=None,
    payload: dict | None = None,
) -> RuntimeCommand:
    return RuntimeCommand.objects.create(
        bot=bot,
        command=command,
        requested_by=requested_by,
        payload=payload or {},
    )


def request_start(bot: Bot, requested_by=None) -> RuntimeCommand:
    bot.desired_state = DesiredState.RUNNING
    bot.status = "starting"
    bot.last_error = ""
    bot.save(update_fields=["desired_state", "status", "last_error", "updated_at"])
    return enqueue_runtime_command(bot, RuntimeCommand.Command.START, requested_by)


def request_stop(bot: Bot, requested_by=None) -> RuntimeCommand:
    bot.desired_state = DesiredState.STOPPED
    bot.status = "stopped"
    bot.save(update_fields=["desired_state", "status", "updated_at"])
    return enqueue_runtime_command(bot, RuntimeCommand.Command.STOP, requested_by)


def request_restart(bot: Bot, requested_by=None) -> RuntimeCommand:
    bot.desired_state = DesiredState.RUNNING
    bot.status = "starting"
    bot.save(update_fields=["desired_state", "status", "updated_at"])
    return enqueue_runtime_command(bot, RuntimeCommand.Command.RESTART, requested_by)


def request_reload(bot: Bot, requested_by=None) -> RuntimeCommand:
    """Ask Runtime to re-read the published config without a full restart."""
    bot.desired_state = DesiredState.RUNNING
    bot.save(update_fields=["desired_state", "updated_at"])
    return enqueue_runtime_command(bot, RuntimeCommand.Command.RELOAD, requested_by)


def replace_bot_token(bot: Bot, token: str, requested_by=None) -> Bot:
    """Validate and persist a new bot token.

    The plain token is never stored or returned. If the bot should be running,
    Runtime gets a ``reload`` command so the new token is applied without
    recreating the bot project.
    """
    user = validate_bot_token(token)
    bot.token_encrypted = encrypt_bot_token(token)
    bot.discord_bot_user_id = str(user.get("id", ""))
    try:
        application = fetch_bot_application(token)
    except DiscordAPIError:
        application = {}
    application_id = str(application.get("id", ""))
    if application_id:
        bot.discord_application_id = application_id
    bot.last_error = ""
    bot.last_error_at = None
    bot.save(
        update_fields=[
            "token_encrypted",
            "discord_bot_user_id",
            "discord_application_id",
            "last_error",
            "last_error_at",
            "updated_at",
        ]
    )
    if bot.desired_state == DesiredState.RUNNING:
        request_reload(bot, requested_by)
    return bot


def sync_bot_guilds(bot: Bot, guilds: list[dict]) -> int:
    """Upsert the guilds reported by Runtime and mark disappeared ones as left."""
    seen: set[str] = set()
    for item in guilds:
        guild_id = str(item.get("id") or item.get("guild_id") or "").strip()
        if not guild_id:
            continue
        guild_name = str(item.get("name") or item.get("guild_name") or "")
        BotGuild.all_objects.update_or_create(
            bot=bot,
            guild_id=guild_id,
            defaults={
                "guild_name": guild_name,
                "left_at": None,
                "deleted_at": None,
            },
        )
        seen.add(guild_id)

    BotGuild.all_objects.filter(bot=bot, left_at__isnull=True).exclude(guild_id__in=seen).update(
        left_at=timezone.now(), updated_at=timezone.now()
    )
    return len(seen)
