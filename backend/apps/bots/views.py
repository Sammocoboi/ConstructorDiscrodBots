"""Bot API: CRUD, lifecycle and guild settings."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsOwner

from .models import Bot, BotGuild, BotRuntimeState, BotVersion, RuntimeCommand
from .serializers import (
    BotCreateSerializer,
    BotGuildSerializer,
    BotRuntimeStateSerializer,
    BotSerializer,
    BotStatusSerializer,
    BotUpdateSerializer,
    BotVersionListSerializer,
    BotVersionSerializer,
    RuntimeCommandSerializer,
)
from .services import request_restart, request_start, request_stop


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

    @extend_schema(request=BotCreateSerializer, responses={201: BotSerializer}, summary="Создать бота")
    def create(self, request, *args, **kwargs):
        serializer = BotCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bot = serializer.save()
        return Response(BotSerializer(bot).data, status=status.HTTP_201_CREATED)

    def _lifecycle_response(self, bot: Bot, command: RuntimeCommand):
        return Response(
            {
                "bot": BotSerializer(bot).data,
                "runtime_command": RuntimeCommandSerializer(command).data,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(request=None, responses={202: RuntimeCommandSerializer}, summary="Запустить бота")
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        bot = self.get_object()
        command = request_start(bot, request.user)
        return self._lifecycle_response(bot, command)

    @extend_schema(request=None, responses={202: RuntimeCommandSerializer}, summary="Остановить бота")
    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        bot = self.get_object()
        command = request_stop(bot, request.user)
        return self._lifecycle_response(bot, command)

    @extend_schema(request=None, responses={202: RuntimeCommandSerializer}, summary="Перезапустить бота")
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

    @extend_schema(responses={200: RuntimeCommandSerializer(many=True)}, summary="История команд запуска")
    @action(detail=True, methods=["get"])
    def commands(self, request, pk=None):
        bot = self.get_object()
        return Response(RuntimeCommandSerializer(bot.runtime_commands.all()[:50], many=True).data)

    @extend_schema(responses={200: BotVersionListSerializer(many=True)}, summary="Версии конфигурации")
    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        bot = self.get_object()
        return Response(BotVersionListSerializer(bot.versions.all(), many=True).data)

    @extend_schema(responses={200: BotGuildSerializer(many=True)}, summary="Гильдии бота")
    @action(detail=True, methods=["get"])
    def guilds(self, request, pk=None):
        bot = self.get_object()
        return Response(BotGuildSerializer(bot.guilds.all(), many=True).data)


class BotGuildDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = BotGuildSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "guild_id"
    lookup_url_kwarg = "guild_id"
    queryset = BotGuild.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BotGuild.objects.none()
        return BotGuild.objects.filter(
            bot_id=self.kwargs["bot_id"], bot__owner=self.request.user
        )


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
