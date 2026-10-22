from __future__ import annotations

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import BotGuild

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BotGuild)
@receiver(post_delete, sender=BotGuild)
def invalidate_user_guilds_on_bot_guild_change(sender, instance, **kwargs):
    try:
        if instance.bot_id and instance.bot.owner_id:
            cache.delete(f"discord:guilds:{instance.bot.owner_id}")
    except Exception:
        logger.exception("Failed to invalidate discord guilds cache for user %s", getattr(instance, "bot_id", None))
