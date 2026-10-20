
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django.shortcuts import get_object_or_404

from backend.apps.bots.models import Bot, BotGuild
from backend.apps.modules.registry import ModuleRegistry
from backend.apps.modules.serializers import (
    ModuleManifestSerializer,
    UpdateModuleSettingsSerializer,
)

class ModuleListView(APIView):
    def get(self, request):
        modules = ModuleRegistry.list_all()
        return Response(modules)

class ModuleDetailView(APIView):
    def get(self, request, slug):
        manifest = ModuleRegistry.get_by_slug(slug)
        if not manifest:
            raise NotFound(f"Модуль '{slug}' не найден")
        return Response(manifest)

class BotModulesView(APIView):
    def get(self, request, bot_id):
        bot = get_object_or_404(Bot, id=bot_id, deleted_at__isnull=True)
        guild_id = request.query_params.get("guild_id")
        
        enabled_modules = []
        guild_settings = {}
        if guild_id:
            bot_guild = BotGuild.objects.filter(bot=bot, guild_id=guild_id).first()
            if bot_guild:
                enabled_modules = bot_guild.enabled_modules or []
                guild_settings = bot_guild.settings or {}

        modules_data = []
        for mod in ModuleRegistry.list_all():
            slug = mod["slug"]
            is_enabled = slug in enabled_modules
            modules_data.append({
                "manifest": mod,
                "enabled": is_enabled,
                "current_settings": guild_settings.get(slug, {})
            })

        return Response({
            "bot_id": str(bot.id),
            "guild_id": guild_id,
            "modules": modules_data
        })

class BotModuleUpdateView(APIView):
    def put(self, request, bot_id, slug):
        bot = get_object_or_404(Bot, id=bot_id, deleted_at__isnull=True)
        manifest = ModuleRegistry.get_by_slug(slug)
        if not manifest:
            raise NotFound(f"Модуль '{slug}' не найден")

        serializer = UpdateModuleSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        guild_id = serializer.validated_data["guild_id"]
        enabled = serializer.validated_data["enabled"]
        settings_dict = serializer.validated_data.get("settings", {})
        bot_perms = serializer.validated_data.get("bot_permissions", 0)
        bot_highest_role_pos = serializer.validated_data.get("bot_highest_role_pos", 100)
        target_role_pos = serializer.validated_data.get("target_role_pos")

        if settings_dict:
            ModuleRegistry.validate_settings(slug, settings_dict)

        check_result = ModuleRegistry.check_permissions_and_hierarchy(
            slug=slug,
            bot_permissions_int=bot_perms,
            bot_highest_role_pos=bot_highest_role_pos,
            target_role_pos=target_role_pos
        )

        bot_guild, _ = BotGuild.objects.get_or_create(bot=bot, guild_id=guild_id)
        current_enabled = set(bot_guild.enabled_modules or [])
        
        if enabled:
            current_enabled.add(slug)
        else:
            current_enabled.discard(slug)
            
        bot_guild.enabled_modules = list(current_enabled)
        
        if settings_dict:
            bot_guild.settings[slug] = settings_dict
            
        bot_guild.save()

        return Response({
            "status": "success",
            "bot_id": str(bot.id),
            "guild_id": guild_id,
            "module_slug": slug,
            "enabled": enabled,
            "settings": bot_guild.settings.get(slug, {}),
            "validation": check_result,
        })
