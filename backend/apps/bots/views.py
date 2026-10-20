
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from backend.apps.bots.models import Bot, BotGuild, BotStatus, DesiredState
from backend.apps.bots.serializers import (
    BotSerializer,
    BotCreateSerializer,
    BotTokenValidateSerializer,
    BotTokenUpdateSerializer,
    BotSyncCommandsSerializer,
    BotGuildSerializer,
)
from backend.apps.bots.services import BotService
from backend.integrations.discord.cache import default_discord_cache

class BotViewSet(viewsets.ModelViewSet):
    queryset = Bot.objects.filter(deleted_at__isnull=True)
    serializer_class = BotSerializer

    def get_queryset(self):
        qs = Bot.objects.filter(deleted_at__isnull=True)
        if self.action == "list":
            owner_id = self.request.query_params.get("owner_id")
            if owner_id:
                return qs.filter(owner_id=owner_id)
        return qs

    def create(self, request, *args, **kwargs):
        owner_id = request.data.get("owner_id", "default-user")
        plan_name = request.data.get("plan_name", "free")
        serializer = BotCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bot = serializer.save(owner_id=owner_id, plan_name=plan_name)
        return Response(BotSerializer(bot).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.desired_state = DesiredState.STOPPED
        instance.status = BotStatus.STOPPED
        instance.save()

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        bot = self.get_object()
        if not bot.token_encrypted:
            return Response(
                {"code": "MISSING_TOKEN", "message": "Невозможно запустить бота без токена Discord"},
                status=status.HTTP_400_BAD_REQUEST
            )
        bot.desired_state = DesiredState.RUNNING
        bot.status = BotStatus.STARTING
        bot.save(update_fields=["desired_state", "status"])
        return Response({"status": "starting", "desired_state": "running", "bot_id": str(bot.id)})

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        bot = self.get_object()
        bot.desired_state = DesiredState.STOPPED
        bot.status = BotStatus.STOPPED
        bot.save(update_fields=["desired_state", "status"])
        return Response({"status": "stopped", "desired_state": "stopped", "bot_id": str(bot.id)})

    @action(detail=True, methods=["post"])
    def restart(self, request, pk=None):
        bot = self.get_object()
        if not bot.token_encrypted:
            return Response(
                {"code": "MISSING_TOKEN", "message": "Невозможно перезапустить бота без токена Discord"},
                status=status.HTTP_400_BAD_REQUEST
            )
        bot.desired_state = DesiredState.RUNNING
        bot.status = BotStatus.STARTING
        bot.save(update_fields=["desired_state", "status"])
        return Response({"status": "restarting", "desired_state": "running", "bot_id": str(bot.id)})

    @action(detail=True, methods=["post"], url_path="token/validate")
    def validate_token(self, request, pk=None):
        bot = self.get_object()
        serializer = BotTokenValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["token"]
        bot_info = BotService.validate_discord_token(raw_token)
        return Response({"valid": True, "bot": bot_info})

    @action(detail=False, methods=["post"], url_path="validate-token")
    def standalone_validate_token(self, request):
        serializer = BotTokenValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["token"]
        bot_info = BotService.validate_discord_token(raw_token)
        return Response({"valid": True, "bot": bot_info})

    @action(detail=True, methods=["put"], url_path="token")
    def update_token(self, request, pk=None):
        bot = self.get_object()
        serializer = BotTokenUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["token"]
        bot = BotService.update_bot_token(bot, raw_token)
        return Response(BotSerializer(bot).data)

    @action(detail=True, methods=["get"], url_path="invite-url")
    def invite_url(self, request, pk=None):
        bot = self.get_object()
        guild_id = request.query_params.get("guild_id")
        result = BotService.get_invite_url(bot, guild_id=guild_id)
        return Response(result)

    @action(detail=True, methods=["post"], url_path="commands/sync")
    def sync_commands(self, request, pk=None):
        bot = self.get_object()
        serializer = BotSyncCommandsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        commands = serializer.validated_data["commands"]
        test_guild_id = serializer.validated_data.get("test_guild_id")
        force = serializer.validated_data.get("force", False)

        result = BotService.sync_slash_commands(
            bot=bot,
            commands_list=commands,
            test_guild_id=test_guild_id,
            force=force
        )
        return Response(result)

class BotGuildViewSet(viewsets.ModelViewSet):
    serializer_class = BotGuildSerializer

    def get_queryset(self):
        bot_id = self.kwargs.get("bot_pk")
        return BotGuild.objects.filter(bot_id=bot_id)

    def get_bot(self) -> Bot:
        bot_id = self.kwargs.get("bot_pk")
        return get_object_or_404(Bot, id=bot_id, deleted_at__isnull=True)

    @action(detail=True, methods=["get"])
    def channels(self, request, bot_pk=None, pk=None):
        bot_guild = self.get_object()
        bot = bot_guild.bot
        client = BotService.get_bot_client(bot)
        
        cache_key = f"guild:{bot_guild.guild_id}:channels"
        channels = default_discord_cache.get_or_set(
            cache_key,
            lambda: client.get_guild_channels(bot_guild.guild_id),
            ttl=60
        )
        return Response({"guild_id": bot_guild.guild_id, "channels": channels})

    @action(detail=True, methods=["get"])
    def roles(self, request, bot_pk=None, pk=None):
        bot_guild = self.get_object()
        bot = bot_guild.bot
        client = BotService.get_bot_client(bot)
        
        cache_key = f"guild:{bot_guild.guild_id}:roles"
        roles = default_discord_cache.get_or_set(
            cache_key,
            lambda: client.get_guild_roles(bot_guild.guild_id),
            ttl=60
        )
        return Response({"guild_id": bot_guild.guild_id, "roles": roles})

    @action(detail=True, methods=["get"])
    def emojis(self, request, bot_pk=None, pk=None):
        bot_guild = self.get_object()
        bot = bot_guild.bot
        client = BotService.get_bot_client(bot)
        
        cache_key = f"guild:{bot_guild.guild_id}:emojis"
        emojis = default_discord_cache.get_or_set(
            cache_key,
            lambda: client.get_guild_emojis(bot_guild.guild_id),
            ttl=60
        )
        return Response({"guild_id": bot_guild.guild_id, "emojis": emojis})

    @action(detail=True, methods=["patch"], url_path="settings")
    def update_settings(self, request, bot_pk=None, pk=None):
        bot_guild = self.get_object()
        new_settings = request.data.get("settings", {})
        enabled_modules = request.data.get("enabled_modules")
        
        if enabled_modules is not None:
            bot_guild.enabled_modules = enabled_modules
        
        if isinstance(new_settings, dict):
            bot_guild.settings.update(new_settings)
            
        bot_guild.save()
        return Response(BotGuildSerializer(bot_guild).data)

class UserDiscordGuildsView(APIView):
    def get(self, request):
        user_oauth_token = request.headers.get("X-Discord-User-Token") or request.query_params.get("oauth_token")
        
        if user_oauth_token:
            client = DiscordRestClient()
            raw_guilds = client.get_user_guilds(user_oauth_token)
            result = []
            for g in raw_guilds:
                perms = int(g.get("permissions", 0))
                is_owner = g.get("owner", False)
                can_manage = is_owner or bool(perms & 0x00000020) or bool(perms & 0x00000008)
                if can_manage:
                    has_bot = BotGuild.objects.filter(guild_id=g["id"]).exists()
                    result.append({
                        "id": g["id"],
                        "name": g["name"],
                        "icon": g.get("icon"),
                        "owner": is_owner,
                        "bot_joined": has_bot,
                    })
            return Response(result)

        return Response([
            {
                "id": "111222333444555666",
                "name": "Тестовый сервер разработчика",
                "icon": None,
                "owner": True,
                "bot_joined": False,
            }
        ])
