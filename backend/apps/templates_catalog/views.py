"""Template catalog API."""

from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.bots.models import Bot, BotDraft, BotVersion
from apps.common.permissions import IsAuthorOrReadOnly

from .models import Template, TemplateVersion
from .serializers import (
    InstantiateTemplateSerializer,
    TemplateCreateSerializer,
    TemplateImportSerializer,
    TemplateSerializer,
    TemplateUpdateSerializer,
    TemplateVersionSerializer,
)


class TemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    queryset = Template.objects.none()
    search_fields = ("title", "description")
    filterset_fields = ("category", "visibility", "is_system")
    ordering_fields = ("created_at", "title", "popularity")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Template.objects.none()
        user = self.request.user
        return (
            Template.objects.filter(
                Q(is_system=True)
                | Q(visibility__in=[Template.Visibility.PUBLIC, Template.Visibility.UNLISTED])
                | Q(author=user)
            )
            .prefetch_related("versions")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "create":
            return TemplateCreateSerializer
        if self.action in {"update", "partial_update"}:
            return TemplateUpdateSerializer
        return TemplateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return Response(TemplateSerializer(template).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return Response(TemplateSerializer(template).data)

    @extend_schema(responses={200: TemplateVersionSerializer(many=True)}, summary="Версии шаблона")
    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        template = self.get_object()
        return Response(TemplateVersionSerializer(template.versions.all(), many=True).data)

    @extend_schema(
        request=InstantiateTemplateSerializer,
        responses={201: OpenApiResponse(description="Bot created from template")},
        summary="Создать бота из шаблона",
    )
    @action(detail=True, methods=["post"])
    def instantiate(self, request, pk=None):
        template = self.get_object()
        serializer = InstantiateTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        version = None
        version_id = serializer.validated_data.get("version_id")
        if version_id:
            version = template.versions.filter(id=version_id).first()
        if version is None:
            version = template.versions.first()
        content = version.content if version else {}

        bot = Bot.objects.create(
            owner=request.user,
            name=serializer.validated_data.get("name") or template.title,
            profile=content.get("profile", {}),
            intents=content.get("intents", []),
        )
        BotDraft.objects.create(bot=bot, content=content, updated_by=request.user)
        bot_version = BotVersion.objects.create(
            bot=bot,
            version_number=1,
            content=content,
            comment=f"Создано из шаблона «{template.title}»",
            created_by=request.user,
        )
        bot.active_version = bot_version
        bot.save(update_fields=["active_version", "updated_at"])
        Template.objects.filter(id=template.id).update(popularity=template.popularity + 1)

        return Response(
            {"bot_id": str(bot.id), "name": bot.name, "template_id": str(template.id)},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=TemplateImportSerializer,
        responses={201: TemplateSerializer},
        summary="Импортировать шаблон из JSON",
    )
    @action(detail=False, methods=["post"], url_path="import")
    def import_json(self, request):
        serializer = TemplateImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = Template.objects.create(
            author=request.user,
            title=data["title"],
            description=data.get("description", ""),
            category=data.get("category", ""),
            visibility=Template.Visibility.PRIVATE,
        )
        TemplateVersion.objects.create(
            template=template,
            version=data.get("version", "1.0.0"),
            content=data["content"],
        )
        return Response(TemplateSerializer(template).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: OpenApiResponse(description="Template JSON")}, summary="Экспортировать шаблон")
    @action(detail=True, methods=["get"])
    def export(self, request, pk=None):
        template = self.get_object()
        version = template.versions.first()
        return Response(
            {
                "title": template.title,
                "description": template.description,
                "category": template.category,
                "version": version.version if version else "1.0.0",
                "content": version.content if version else {},
            }
        )

    @extend_schema(responses={200: OpenApiResponse(description="Share link")}, summary="Ссылка на шаблон")
    @action(detail=True, methods=["post"])
    def share_link(self, request, pk=None):
        template = self.get_object()
        if template.author_id != request.user.id:
            raise PermissionDenied("Only the author can share a template")
        template.visibility = Template.Visibility.UNLISTED
        template.save(update_fields=["visibility", "updated_at"])
        from django.conf import settings

        return Response(
            {"url": f"{settings.FRONTEND_URL}/templates/{template.id}", "visibility": template.visibility}
        )
