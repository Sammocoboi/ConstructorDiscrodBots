"""
DRF-сериализаторы для API управления ботами и гильдиями.
"""

from rest_framework import serializers
from backend.apps.bots.models import Bot, BotGuild, BotStatus, DesiredState
from backend.apps.bots.services import BotService


class BotSerializer(serializers.ModelSerializer):
    token_masked = serializers.CharField(read_only=True)
    guilds_count = serializers.SerializerMethodField()

    class Meta:
        model = Bot
        fields = [
            "id",
            "name",
            "status",
            "desired_state",
            "discord_application_id",
            "discord_bot_user_id",
            "discriminator",
            "avatar_url",
            "token_masked",
            "last_error",
            "last_error_at",
            "profile",
            "intents",
            "guilds_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "token_masked",
            "last_error",
            "last_error_at",
            "discord_application_id",
            "discord_bot_user_id",
            "created_at",
            "updated_at",
        ]

    def get_guilds_count(self, obj: Bot) -> int:
        return obj.guilds.count()


class BotCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, default="Новый бот")
    token = serializers.CharField(required=False, allow_blank=True, write_only=True)
    plan_name = serializers.CharField(default="free", write_only=True)

    def create(self, validated_data):
        owner_id = validated_data.get("owner_id", "default-user")
        plan_name = validated_data.get("plan_name", "free")
        
        # Проверяем лимиты тарифа (SAN-1, FR-4.10)
        BotService.check_bot_limit(owner_id=owner_id, plan_name=plan_name)

        bot = Bot.objects.create(
            name=validated_data.get("name", "Новый бот"),
            owner_id=owner_id
        )

        raw_token = validated_data.get("token")
        if raw_token:
            BotService.update_bot_token(bot, raw_token)

        return bot


class BotTokenValidateSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)


class BotTokenUpdateSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)


class BotSyncCommandsSerializer(serializers.Serializer):
    commands = serializers.ListField(child=serializers.DictField(), required=True)
    test_guild_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    force = serializers.BooleanField(default=False)


class BotGuildSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotGuild
        fields = [
            "id",
            "guild_id",
            "guild_name",
            "icon_url",
            "joined_at",
            "enabled_modules",
            "settings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "joined_at", "created_at", "updated_at"]
