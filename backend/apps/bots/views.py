"""Bot API: CRUD, lifecycle and guild settings."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsOwner, IsRuntimeService
from integrations.discord.permissions import calculate_permissions_integer, generate_invite_url

from .models import Bot, BotGuild, BotRuntimeState, BotVersion, RuntimeCommand
from .serializers import (
    BotCreateSerializer,
    BotGuildSerializer,
    BotGuildSyncSerializer,
    BotRuntimeStateSerializer,
    BotSerializer,
    BotStatusSerializer,
    BotTokenInputSerializer,
    BotTokenValidationSerializer,
    BotUpdateSerializer,
    BotVersionListSerializer,
    BotVersionSerializer,
    RuntimeCommandSerializer,
)
from .services import (
    DiscordAPIError,
    inspect_bot_token,
    replace_bot_token,
    request_restart,
    request_start,
    request_stop,
    sync_bot_guilds,
    validate_bot_token,
)

AVATAR_COLORS = ("#5865f2", "#00a8fc", "#3ba55d", "#faa81a", "#ed4245", "#9b59b6")


def _avatar_color(value: str) -> str:
    if not value:
        return AVATAR_COLORS[0]
    try:
        index = int(value)
    except ValueError:
        index = sum(ord(char) for char in value)
    return AVATAR_COLORS[index % len(AVATAR_COLORS)]


class BotViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Bot.objects.none()
    search_fields = ("name", "discord_application_id")
    filterset_fields = ("status", "desired_state")
    ordering_fields = ("created_at", "name", "status")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Bot.objects.none()
        return (
            Bot.objects.filter(owner=self.request.user)
            .select_related("active_version", "runtime_state")
            .all()
        )

    def get_serializer_class(self):
        if self.action == "create":
            return BotCreateSerializer
        if self.action in {"update", "partial_update"}:
            return BotUpdateSerializer
        return BotSerializer

    @extend_schema(
        request=BotCreateSerializer, responses={201: BotSerializer}, summary="Создать бота"
    )
    def create(self, request, *args, **kwargs):
        serializer = BotCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bot = serializer.save()
        return Response(BotSerializer(bot).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=BotTokenInputSerializer,
        responses={200: BotTokenValidationSerializer},
        summary="Проверить токен Discord-бота",
    )
    @action(detail=False, methods=["post"], url_path="validate-token")
    def validate_token(self, request):
        serializer = BotTokenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        try:
            inspected = inspect_bot_token(token)
        except DiscordAPIError as exc:
            return Response(
                {"valid": False, "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = inspected["user"]
        application = inspected["application"]
        guilds = inspected["guilds"]
        payload = {
            "valid": True,
            "username": user.get("global_name") or user.get("username") or "",
            "applicationId": str(application.get("id", "")),
            "avatarColor": _avatar_color(str(user.get("id", ""))),
            "guildsCount": len(guilds),
        }
        return Response(BotTokenValidationSerializer(payload).data)

    @extend_schema(
        request=BotTokenInputSerializer,
        responses={200: BotSerializer},
        summary="Заменить токен бота",
    )
    @action(detail=True, methods=["post"], url_path="token")
    def token(self, request, pk=None):
        bot = self.get_object()
        serializer = BotTokenInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            bot = replace_bot_token(bot, serializer.validated_data["token"], request.user)
        except DiscordAPIError as exc:
            return Response(
                {"token": [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(BotSerializer(bot).data)

    def _lifecycle_response(self, bot: Bot, command: RuntimeCommand):
        return Response(
            {
                "bot": BotSerializer(bot).data,
                "runtime_command": RuntimeCommandSerializer(command).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        request=None, responses={202: RuntimeCommandSerializer}, summary="Запустить бота"
    )
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        bot = self.get_object()
        command = request_start(bot, request.user)
        return self._lifecycle_response(bot, command)

    @extend_schema(
        request=None, responses={202: RuntimeCommandSerializer}, summary="Остановить бота"
    )
    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        bot = self.get_object()
        command = request_stop(bot, request.user)
        return self._lifecycle_response(bot, command)

    @extend_schema(
        request=None, responses={202: RuntimeCommandSerializer}, summary="Перезапустить бота"
    )
    @action(detail=True, methods=["post"])
    def restart(self, request, pk=None):
        bot = self.get_object()
        command = request_restart(bot, request.user)
        return self._lifecycle_response(bot, command)

    @extend_schema(responses={200: BotStatusSerializer}, summary="Статус и runtime-состояние")
    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        bot = self.get_object()
        runtime = BotRuntimeState.objects.filter(bot=bot).first()
        data = {
            "bot_id": bot.id,
            "status": bot.status,
            "desired_state": bot.desired_state,
            "runtime": BotRuntimeStateSerializer(runtime).data if runtime else None,
        }
        return Response(data)

    @extend_schema(
        responses={200: RuntimeCommandSerializer(many=True)}, summary="История команд запуска"
    )
    @action(detail=True, methods=["get"])
    def commands(self, request, pk=None):
        bot = self.get_object()
        return Response(RuntimeCommandSerializer(bot.runtime_commands.all()[:50], many=True).data)

    @extend_schema(
        responses={200: BotVersionListSerializer(many=True)}, summary="Версии конфигурации"
    )
    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        bot = self.get_object()
        return Response(BotVersionListSerializer(bot.versions.all(), many=True).data)

    @extend_schema(responses={200: BotGuildSerializer(many=True)}, summary="Гильдии бота")
    @action(detail=True, methods=["get"])
    def guilds(self, request, pk=None):
        bot = self.get_object()
        return Response(BotGuildSerializer(bot.guilds.all(), many=True).data)

    @extend_schema(
        request=None,
        responses={200: None},
        summary="Сгенерировать invite-ссылку для бота",
    )
    @action(detail=True, methods=["get"], url_path="invite-url")
    def invite_url(self, request, pk=None):
        bot = self.get_object()
        if not bot.discord_application_id:
            return Response(
                {"detail": "discord_application_id is required for invite URL"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        guild_id = request.query_params.get("guild_id")
        disable_guild_select = request.query_params.get("disable_guild_select") == "true"
        enabled_modules = list(
            BotGuild.objects.filter(bot=bot, left_at__isnull=True)
            .values_list("enabled_modules", flat=True)
            .first()
            or []
        )
        permissions = calculate_permissions_integer(enabled_modules)
        url = generate_invite_url(
            bot.discord_application_id,
            permissions,
            guild_id=guild_id,
            disable_guild_select=disable_guild_select,
        )
        return Response({"url": url, "permissions": permissions})


class ValidateTokenView(generics.GenericAPIView):
    """Validate a Discord bot token without creating a bot."""

    permission_classes = [IsAuthenticated]

    class InputSerializer(drf_serializers.Serializer):
        token = drf_serializers.CharField()

    @extend_schema(
        request=InputSerializer,
        responses={200: None},
        summary="Проверить Discord-токен бота",
    )
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        try:
            discord_user = validate_bot_token(token)
        except DiscordAPIError as exc:
            return Response(
                {"valid": False, "error": str(exc)},
                status=status.HTTP_200_OK,
            )
        avatar = discord_user.get("avatar", "")
        user_id = discord_user.get("id", "")
        avatar_color = "#5865F2"
        if avatar:
            avatar_color = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png"
        return Response(
            {
                "valid": True,
                "username": discord_user.get("username", ""),
                "applicationId": user_id,
                "avatarColor": avatar_color,
                "guildsCount": 0,
            },
            status=status.HTTP_200_OK,
        )


class BotGuildDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = BotGuildSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "guild_id"
    lookup_url_kwarg = "guild_id"
    queryset = BotGuild.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BotGuild.objects.none()
        return BotGuild.objects.filter(bot_id=self.kwargs["bot_id"], bot__owner=self.request.user)


class BotGuildSyncView(APIView):
    """Internal endpoint used by Runtime to mirror Discord guild membership."""

    permission_classes = [IsRuntimeService]
    authentication_classes = []

    @extend_schema(
        request=BotGuildSyncSerializer,
        responses={200: OpenApiResponse(description="Guilds synced")},
        summary="Синхронизировать гильдии бота (Runtime)",
    )
    def post(self, request, bot_id):
        bot = get_object_or_404(Bot, id=bot_id)
        serializer = BotGuildSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        synced = sync_bot_guilds(bot, serializer.validated_data["guilds"])
        return Response({"synced": synced}, status=status.HTTP_200_OK)


class BotVersionDetailView(generics.RetrieveAPIView):
    serializer_class = BotVersionSerializer
    permission_classes = [IsAuthenticated]
    queryset = BotVersion.objects.none()

    def get_object(self):
        return get_object_or_404(
            BotVersion,
            id=self.kwargs["version_id"],
            bot_id=self.kwargs["bot_id"],
            bot__owner=self.request.user,
        )
