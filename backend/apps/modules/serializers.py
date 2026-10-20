"""
Сериализаторы для модулей и валидации их настроек.
"""

from rest_framework import serializers

class ModuleManifestSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    is_premium = serializers.BooleanField()
    min_plan = serializers.CharField()
    required_permissions = serializers.IntegerField()
    required_intents = serializers.ListField(child=serializers.CharField())
    commands = serializers.ListField(child=serializers.CharField())
    events = serializers.ListField(child=serializers.CharField())
    dangerous_actions = serializers.BooleanField()
    settings_schema = serializers.DictField()


class UpdateModuleSettingsSerializer(serializers.Serializer):
    guild_id = serializers.CharField(required=True)
    enabled = serializers.BooleanField(required=True)
    settings = serializers.DictField(required=False, default=dict)
    bot_permissions = serializers.IntegerField(required=False, default=0)
    bot_highest_role_pos = serializers.IntegerField(required=False, default=100)
    target_role_pos = serializers.IntegerField(required=False, allow_null=True, default=None)
