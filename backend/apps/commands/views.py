from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bots.models import Bot, BotGuild

from .models import CommandLibrary
from .registry import CommandLibraryRegistry
from .serializers import (
    CommandLibraryListSerializer,
    CommandLibrarySerializer,
    CommandPermissionsUpdateSerializer,
    InstallCommandsRequestSerializer,
)


class CommandLibraryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CommandLibrary.objects.filter(is_active=True)
    filterset_fields = ("category", "type", "is_active")
    search_fields = ("title", "description", "slug")
    ordering_fields = ("title", "popularity", "category")

    def get_serializer_class(self):
        if self.action == "list":
            return CommandLibraryListSerializer
        return CommandLibrarySerializer


class CommandCategoriesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CommandLibraryRegistry.get_categories())


class BotInstallCommandsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
        serializer = InstallCommandsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        slugs = serializer.validated_data.get("slugs", [])
        category = serializer.validated_data.get("category")
        conflict_action = serializer.validated_data.get("action_on_conflict", "replace")
        guild_id = serializer.validated_data.get("guild_id")

        target_commands = []
        if category:
            target_commands = CommandLibraryRegistry.list_commands(category=category)
        elif slugs:
            for slug in slugs:
                command = CommandLibraryRegistry.get_by_slug(slug)
                if command:
                    target_commands.append(command)

        if not target_commands:
            raise ValidationError("Не указаны команды для установки")

        profile = bot.profile or {}
        bot_commands = profile.get("installed_commands", {})
        existing_names = list(bot_commands.keys())

        installed = []
        conflicts_handled = []
        auto_enabled_modules = set()

        for command in target_commands:
            name = command["name"]
            slug = command["slug"]

            conflict_info = CommandLibraryRegistry.check_name_conflict(
                existing_names, name
            )
            if conflict_info["has_conflict"]:
                if conflict_action == "skip":
                    conflicts_handled.append(
                        {
                            "name": name,
                            "action": "skipped",
                            "reason": "Команда с таким именем уже существует",
                        }
                    )
                    continue
                if conflict_action == "rename":
                    name = conflict_info["suggested_name"]
                    conflicts_handled.append(
                        {
                            "original_name": command["name"],
                            "new_name": name,
                            "action": "renamed",
                        }
                    )
                elif conflict_action == "replace":
                    conflicts_handled.append({"name": name, "action": "replaced"})

            installed_command = dict(command)
            installed_command["name"] = name
            installed_command["installed_at"] = str(request.user)

            bot_commands[name] = installed_command
            if name not in existing_names:
                existing_names.append(name)

            dependency = CommandLibraryRegistry.resolve_dependencies(slug)
            if dependency["required_module"]:
                auto_enabled_modules.add(dependency["required_module"])

            installed.append(
                {
                    "slug": slug,
                    "name": name,
                    "required_module": dependency["required_module"],
                }
            )

        profile["installed_commands"] = bot_commands
        bot.profile = profile
        bot.save(update_fields=["profile"])

        if guild_id and auto_enabled_modules:
            bot_guild, _ = BotGuild.objects.get_or_create(bot=bot, guild_id=guild_id)
            current_modules = set(bot_guild.enabled_modules or [])
            current_modules.update(auto_enabled_modules)
            bot_guild.enabled_modules = list(current_modules)
            bot_guild.save(update_fields=["enabled_modules"])

        return Response(
            {
                "status": "success",
                "bot_id": str(bot.id),
                "installed_count": len(installed),
                "installed_commands": installed,
                "conflicts_handled": conflicts_handled,
                "auto_enabled_modules": list(auto_enabled_modules),
            }
        )


class BotCommandPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, bot_id, command_name):
        bot = get_object_or_404(Bot, id=bot_id, owner=request.user)
        profile = bot.profile or {}
        bot_commands = profile.get("installed_commands", {})

        if command_name not in bot_commands:
            raise NotFound(f"Команда '{command_name}' не установлена в этом боте")

        serializer = CommandPermissionsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_command = bot_commands[command_name]
        target_command["access_rules"] = {
            "default_member_permissions": data.get("default_member_permissions"),
            "allowed_roles": data.get("allowed_roles", []),
            "denied_roles": data.get("denied_roles", []),
            "allowed_channels": data.get("allowed_channels", []),
            "denied_channels": data.get("denied_channels", []),
            "allowed_users": data.get("allowed_users", []),
            "denied_users": data.get("denied_users", []),
            "no_permission_message": data.get("no_permission_message"),
        }
        target_command["cooldown"] = {
            "type": data.get("cooldown_type", "user"),
            "seconds": data.get("cooldown_seconds", 5),
        }

        profile["installed_commands"] = bot_commands
        bot.profile = profile
        bot.save(update_fields=["profile"])

        return Response(
            {
                "status": "success",
                "command_name": command_name,
                "access_rules": target_command["access_rules"],
                "cooldown": target_command["cooldown"],
            }
        )
