"""Template serializers."""

from __future__ import annotations

from rest_framework import serializers

from .models import Template, TemplateVersion


class TemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateVersion
        fields = ("id", "version", "changelog", "content", "created_at")
        read_only_fields = ("id", "created_at")


class TemplateSerializer(serializers.ModelSerializer):
    latest_version = serializers.SerializerMethodField()
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = Template
        fields = (
            "id",
            "title",
            "description",
            "category",
            "visibility",
            "tags",
            "is_system",
            "popularity",
            "author_email",
            "latest_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "is_system",
            "popularity",
            "author_email",
            "created_at",
            "updated_at",
        )

    def get_latest_version(self, obj: Template) -> dict | None:
        version = obj.versions.first()
        return TemplateVersionSerializer(version).data if version else None


class TemplateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ("title", "description", "category", "visibility", "tags")


class TemplateCreateSerializer(serializers.ModelSerializer):
    content = serializers.JSONField(write_only=True, required=False, default=dict)
    version = serializers.CharField(write_only=True, required=False, default="1.0.0")
    changelog = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")

    class Meta:
        model = Template
        fields = (
            "title",
            "description",
            "category",
            "visibility",
            "tags",
            "content",
            "version",
            "changelog",
        )

    def create(self, validated_data):
        content = validated_data.pop("content", {})
        version = validated_data.pop("version", "1.0.0")
        changelog = validated_data.pop("changelog", "")
        template = Template.objects.create(author=self.context["request"].user, **validated_data)
        TemplateVersion.objects.create(
            template=template,
            version=version,
            changelog=changelog,
            content=content,
        )
        return template


class InstantiateTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    version_id = serializers.UUIDField(required=False, allow_null=True)


class TemplateImportSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.CharField(required=False, allow_blank=True, default="")
    version = serializers.CharField(required=False, default="1.0.0")
    content = serializers.JSONField()

    def validate_content(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("content must be a JSON object")
        forbidden = {"token", "token_encrypted", "access_token", "refresh_token", "client_secret"}
        stack = [value]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                if forbidden.intersection({str(key).lower() for key in item}):
                    raise serializers.ValidationError("Template must not contain secrets")
                stack.extend(item.values())
            elif isinstance(item, list):
                stack.extend(item)
        return value
