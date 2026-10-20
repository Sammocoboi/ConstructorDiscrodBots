"""
Сериализаторы для библиотеки команд и процесса установки команд в бота.
"""

from rest_framework import serializers


class CommandCardSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    description = serializers.CharField()
    type = serializers.CharField()
    required_module = serializers.CharField(allow_null=True, required=False)
    required_permissions = serializers.IntegerField(default=0)
    required_intents = serializers.ListField(child=serializers.CharField(), default=list)
    default_member_permissions = serializers.CharField(allow_null=True, required=False)
    cooldown = serializers.DictField(default=dict)
    options = serializers.ListField(child=serializers.DictField(), default=list)
    preview = serializers.DictField(default=dict)
    flow = serializers.DictField(default=dict)


class InstallCommandsRequestSerializer(serializers.Serializer):
    slugs = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    action_on_conflict = serializers.ChoiceField(
        choices=["replace", "rename", "skip"],
        default="replace"
    )
    guild_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CommandPermissionsUpdateSerializer(serializers.Serializer):
    default_member_permissions = serializers.CharField(allow_null=True, required=False)
    allowed_roles = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    denied_roles = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    allowed_channels = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    denied_channels = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    allowed_users = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    denied_users = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    cooldown_type = serializers.ChoiceField(choices=["user", "channel", "guild"], default="user")
    cooldown_seconds = serializers.IntegerField(default=5, min_value=0, max_value=86400)
    no_permission_message = serializers.CharField(
        default="У вас недостаточно прав для использования этой команды."
    )
