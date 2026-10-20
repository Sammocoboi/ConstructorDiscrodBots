"""
API views для каталога библиотеки команд и их установки в проект бота.
Соответствие ТЗ §4.4 (FR-4.1–4.4, FR-4.6) и задачам SAN-8, SAN-10.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
from django.shortcuts import get_object_or_404

from backend.apps.bots.models import Bot, BotGuild
from backend.apps.commands.registry import CommandLibraryRegistry
from backend.apps.commands.serializers import (
    CommandCardSerializer,
    InstallCommandsRequestSerializer,
    CommandPermissionsUpdateSerializer,
)


class CommandLibraryListView(APIView):
    """
    Каталог готовых команд библиотеки (FR-4.1):
    GET /api/v1/commands-library?category={category}&search={search}
    """
    def get(self, request):
        category = request.query_params.get("category")
        search = request.query_params.get("search")
        commands = CommandLibraryRegistry.list_commands(category=category, search=search)
        return Response({
            "total": len(commands),
            "commands": commands
        })


class CommandLibraryDetailView(APIView):
    """
    Карточка готовой команды:
    GET /api/v1/commands-library/{slug}
    """
    def get(self, request, slug):
        cmd = CommandLibraryRegistry.get_by_slug(slug)
        if not cmd:
            raise NotFound(f"Команда '{slug}' не найдена в библиотеке")
        return Response(cmd)


class CommandCategoriesView(APIView):
    """
    Категории готовых команд:
    GET /api/v1/commands-library/categories
    """
    def get(self, request):
        categories = CommandLibraryRegistry.get_categories()
        return Response(categories)


class BotInstallCommandsView(APIView):
    """
    Установка команд из библиотеки в проект бота (SAN-8, FR-4.3):
    POST /api/v1/bots/{bot_id}/commands/install
    Поддерживает одиночную установку, списком или всей категорией.
    Автоматически определяет зависимости и обрабатывает конфликты имён.
    """
    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, id=bot_id, deleted_at__isnull=True)
        serializer = InstallCommandsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        slugs = serializer.validated_data.get("slugs", [])
        category = serializer.validated_data.get("category")
        conflict_action = serializer.validated_data.get("action_on_conflict", "replace")
        guild_id = serializer.validated_data.get("guild_id")

        # Если передана категория, собираем все команды этой категории (FR-4.3: Массовое добавление)
        target_commands = []
        if category:
            target_commands = CommandLibraryRegistry.list_commands(category=category)
        elif slugs:
            for s in slugs:
                cmd = CommandLibraryRegistry.get_by_slug(s)
                if cmd:
                    target_commands.append(cmd)

        if not target_commands:
            raise ValidationError("Не указаны команды для установки")

        # Считываем текущую конфигурацию команд бота (в профиле или черновике)
        bot_commands = bot.profile.get("installed_commands", {})
        existing_names = list(bot_commands.keys())

        installed = []
        conflicts_handled = []
        auto_enabled_modules = set()

        for cmd in target_commands:
            name = cmd["name"]
            slug = cmd["slug"]
            
            # Проверка конфликта имён
            conflict_info = CommandLibraryRegistry.check_name_conflict(existing_names, name)
            if conflict_info["has_conflict"]:
                if conflict_action == "skip":
                    conflicts_handled.append({
                        "name": name,
                        "action": "skipped",
                        "reason": "Команда с таким именем уже существует"
                    })
                    continue
                elif conflict_action == "rename":
                    name = conflict_info["suggested_name"]
                    conflicts_handled.append({
                        "original_name": cmd["name"],
                        "new_name": name,
                        "action": "renamed"
                    })
                elif conflict_action == "replace":
                    conflicts_handled.append({
                        "name": name,
                        "action": "replaced"
                    })

            # Подготовка структуры команды в проекте бота
            installed_cmd = dict(cmd)
            installed_cmd["name"] = name
            installed_cmd["installed_at"] = str(request.user) if hasattr(request, "user") else "system"
            
            # Сохраняем команду в проект бота
            bot_commands[name] = installed_cmd
            if name not in existing_names:
                existing_names.append(name)

            # Проверка зависимостей (FR-4.3: Автоматическое подключение модулей-зависимостей)
            dep = CommandLibraryRegistry.resolve_dependencies(slug)
            if dep["required_module"]:
                auto_enabled_modules.add(dep["required_module"])

            installed.append({
                "slug": slug,
                "name": name,
                "required_module": dep["required_module"]
            })

        # Сохраняем обновленный список команд в профиле бота
        bot.profile["installed_commands"] = bot_commands
        bot.save(update_fields=["profile"])

        # Если указана гильдия, автоматически включаем модули-зависимости (FR-4.3)
        if guild_id and auto_enabled_modules:
            bot_guild, _ = BotGuild.objects.get_or_create(bot=bot, guild_id=guild_id)
            current_mods = set(bot_guild.enabled_modules or [])
            current_mods.update(auto_enabled_modules)
            bot_guild.enabled_modules = list(current_mods)
            bot_guild.save()

        return Response({
            "status": "success",
            "bot_id": str(bot.id),
            "installed_count": len(installed),
            "installed_commands": installed,
            "conflicts_handled": conflicts_handled,
            "auto_enabled_modules": list(auto_enabled_modules),
        })


class BotCommandPermissionsView(APIView):
    """
    Настройка прав, кулдаунов и белых/черных списков команды бота (SAN-10, FR-4.6):
    PUT /api/v1/bots/{bot_id}/commands/{command_name}/permissions
    """
    def put(self, request, bot_id, command_name):
        bot = get_object_or_404(Bot, id=bot_id, deleted_at__isnull=True)
        bot_commands = bot.profile.get("installed_commands", {})
        
        if command_name not in bot_commands:
            raise NotFound(f"Команда '{command_name}' не установлена в этом боте")

        serializer = CommandPermissionsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_cmd = bot_commands[command_name]
        target_cmd["access_rules"] = {
            "default_member_permissions": data.get("default_member_permissions"),
            "allowed_roles": data.get("allowed_roles", []),
            "denied_roles": data.get("denied_roles", []),
            "allowed_channels": data.get("allowed_channels", []),
            "denied_channels": data.get("denied_channels", []),
            "allowed_users": data.get("allowed_users", []),
            "denied_users": data.get("denied_users", []),
            "no_permission_message": data.get("no_permission_message")
        }
        target_cmd["cooldown"] = {
            "type": data.get("cooldown_type", "user"),
            "seconds": data.get("cooldown_seconds", 5)
        }

        bot.profile["installed_commands"] = bot_commands
        bot.save(update_fields=["profile"])

        return Response({
            "status": "success",
            "command_name": command_name,
            "access_rules": target_cmd["access_rules"],
            "cooldown": target_cmd["cooldown"]
        })
