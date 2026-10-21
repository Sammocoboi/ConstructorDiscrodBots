"""Discord and bot lifecycle helpers used by the API layer."""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from apps.common.crypto import encrypt_secret

from .models import Bot, DesiredState, RuntimeCommand

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
    return response.json()


def encrypt_bot_token(token: str) -> str:
    return encrypt_secret(token)


def build_invite_url(application_id: str, permissions: int = 0) -> str:
    if not application_id:
        raise DiscordAPIError("Discord application id is required")
    return (
        "https://discord.com/oauth2/authorize"
        f"?client_id={application_id}&permissions={permissions}&scope=bot%20applications.commands"
    )


def enqueue_runtime_command(bot: Bot, command: str, requested_by=None) -> RuntimeCommand:
    return RuntimeCommand.objects.create(
        bot=bot,
        command=command,
        requested_by=requested_by,
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
