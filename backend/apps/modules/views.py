from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot, BotGuild

from .models import Module
from .registry import ModuleRegistry
from .serializers import ModuleSerializer, UpdateModuleSettingsSerializer


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    queryset = Module.objects.filter(is_active=True)
    filterset_fields = ("is_premium", "min_plan")
    search_fields = ("title", "description")
    ordering_fields = ("title",)


class BotModulesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bot_id):
        bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
        guild_id = request.query_params.get("guild_id")

        enabled_modules: list[str] = []
        guild_settings: dict[str, Any] = {}
        if guild_id:
            bot_guild = BotGuild.objects.filter(bot=bot, guild_id=guild_id).first()
            if bot_guild:
                enabled_modules = bot_guild.enabled_modules or []
                guild_settings = bot_guild.settings or {}

        modules_data = []
        for manifest in ModuleRegistry.list_all():
            slug = manifest["slug"]
            modules_data.append(
                {
                    "manifest": manifest,
                    "enabled": slug in enabled_modules,
                    "current_settings": guild_settings.get(slug, {}),
                }
            )

        return Response(
            {
                "bot_id": str(bot.id),
                "guild_id": guild_id,
                "modules": modules_data,
            }
        )


class BotModuleUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, bot_id, slug):
        bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
        manifest = ModuleRegistry.get_by_slug(slug)
        if not manifest:
            raise NotFound(f"Модуль '{slug}' не найден")

        serializer = UpdateModuleSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        guild_id = serializer.validated_data["guild_id"]
        enabled = serializer.validated_data["enabled"]
        settings_dict = serializer.validated_data.get("settings", {})
        bot_permissions = serializer.validated_data.get("bot_permissions", 0)
        bot_highest_role_pos = serializer.validated_data.get(
            "bot_highest_role_pos", 100
        )
        target_role_pos = serializer.validated_data.get("target_role_pos")

        if settings_dict:
            ModuleRegistry.validate_settings(slug, settings_dict)

        check_result = ModuleRegistry.check_permissions_and_hierarchy(
            slug=slug,
            bot_permissions_int=bot_permissions,
            bot_highest_role_pos=bot_highest_role_pos,
            target_role_pos=target_role_pos,
        )

        bot_guild, _ = BotGuild.objects.get_or_create(bot=bot, guild_id=guild_id)
        current_enabled = set(bot_guild.enabled_modules or [])

        if enabled:
            current_enabled.add(slug)
        else:
            current_enabled.discard(slug)

        bot_guild.enabled_modules = list(current_enabled)

        if settings_dict:
            guild_settings = bot_guild.settings or {}
            guild_settings[slug] = settings_dict
            bot_guild.settings = guild_settings

        bot_guild.save(update_fields=["enabled_modules", "settings"])

        return Response(
            {
                "status": "success",
                "bot_id": str(bot.id),
                "guild_id": guild_id,
                "module_slug": slug,
                "enabled": enabled,
                "settings": (bot_guild.settings or {}).get(slug, {}),
                "validation": check_result,
            }
        )
