"""Bot serializers."""

from __future__ import annotations

from rest_framework import serializers

from .models import (
    Bot,
    BotDraft,
    BotGuild,
    BotRuntimeState,
    BotVariable,
    BotVersion,
    RuntimeCommand,
    ScheduledJob,
)
from .services import DiscordAPIError, encrypt_bot_token, validate_bot_token


class BotSerializer(serializers.ModelSerializer):
    has_token = serializers.BooleanField(read_only=True)
    token_masked = serializers.SerializerMethodField()
    active_version_number = serializers.IntegerField(
        source="active_version.version_number", read_only=True
    )

    class Meta:
        model = Bot
        fields = (
            "id",
            "name",
            "discord_application_id",
            "discord_bot_user_id",
            "status",
            "desired_state",
            "active_version_number",
            "profile",
            "intents",
            "has_token",
            "token_masked",
            "last_error",
            "last_error_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_token_masked(self, obj: Bot) -> str:
        return "••••••••" if obj.has_token else ""


class BotCreateSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Bot
        fields = ("name", "discord_application_id", "token", "profile", "intents")

    def create(self, validated_data):
        from apps.billing.services import ensure_bot_limit

        ensure_bot_limit(self.context["request"].user)

        token = validated_data.pop("token", "")
        owner = self.context["request"].user
        bot = Bot.objects.create(owner=owner, **validated_data)
        if token:
            try:
                discord_user = validate_bot_token(token)
            except DiscordAPIError as exc:
                bot.delete()
                raise serializers.ValidationError({"token": str(exc)}) from exc
            bot.token_encrypted = encrypt_bot_token(token)
            bot.discord_bot_user_id = str(discord_user.get("id", ""))
            bot.save(update_fields=["token_encrypted", "discord_bot_user_id", "updated_at"])
        return bot


class BotUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bot
        fields = ("name", "discord_application_id", "profile", "intents")


class BotGuildSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotGuild
        fields = (
            "id",
            "guild_id",
            "guild_name",
            "joined_at",
            "left_at",
            "settings",
            "enabled_modules",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "guild_id", "joined_at", "left_at", "created_at", "updated_at")


class BotGuildSyncItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True, default="")


class BotGuildSyncSerializer(serializers.Serializer):
    guilds = BotGuildSyncItemSerializer(many=True)


class BotVersionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotVersion
        fields = (
            "id",
            "version_number",
            "comment",
            "published_at",
            "created_at",
        )


class BotVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotVersion
        fields = (
            "id",
            "version_number",
            "content",
            "comment",
            "published_at",
            "created_at",
        )


class BotDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotDraft
        fields = ("id", "content", "updated_at")
        read_only_fields = ("id", "updated_at")


class BotVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotVariable
        fields = ("id", "scope", "guild_id", "user_discord_id", "key", "value", "created_at")
        read_only_fields = ("id", "created_at")


class RuntimeCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuntimeCommand
        fields = (
            "id",
            "command",
            "status",
            "payload",
            "acked_at",
            "finished_at",
            "processed_at",
            "error",
            "created_at",
        )
        read_only_fields = fields


class BotRuntimeStateSerializer(serializers.ModelSerializer):
    is_alive = serializers.BooleanField(read_only=True)

    class Meta:
        model = BotRuntimeState
        fields = (
            "worker_id",
            "status",
            "latency_ms",
            "guild_count",
            "uptime_seconds",
            "version_number",
            "heartbeat_at",
            "started_at",
            "last_error",
            "is_alive",
        )
        read_only_fields = fields


class ScheduledJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledJob
        fields = ("id", "guild_id", "flow_id", "run_at", "cron", "payload", "status")
        read_only_fields = ("id", "status")


class BotStatusSerializer(serializers.Serializer):
    bot_id = serializers.UUIDField()
    status = serializers.CharField()
    desired_state = serializers.CharField()
    runtime = BotRuntimeStateSerializer(allow_null=True)


class BotTokenMaskSerializer(serializers.Serializer):
    token_masked = serializers.CharField()


class BotTokenInputSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=True)


class BotTokenValidationSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    username = serializers.CharField()
    applicationId = serializers.CharField(allow_blank=True)
    avatarColor = serializers.CharField()
    guildsCount = serializers.IntegerField()
