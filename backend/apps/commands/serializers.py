from rest_framework import serializers

from .models import CommandLibrary


class CommandLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandLibrary
        fields = (
            "id",
            "slug",
            "category",
            "title",
            "description",
            "type",
            "options",
            "flow",
            "required_permissions",
            "required_intents",
            "dependencies",
            "popularity",
            "is_active",
        )
        read_only_fields = fields


class CommandLibraryListSerializer(CommandLibrarySerializer):
    class Meta(CommandLibrarySerializer.Meta):
        fields = tuple(  # type: ignore[assignment]  # django-stubs: Meta.fields — произвольный tuple
            field for field in CommandLibrarySerializer.Meta.fields if field != "flow"
        )


class InstallCommandsRequestSerializer(serializers.Serializer):
    slugs = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    action_on_conflict = serializers.ChoiceField(
        choices=["replace", "rename", "skip"], default="replace"
    )
    guild_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CommandPermissionsUpdateSerializer(serializers.Serializer):
    default_member_permissions = serializers.CharField(
        allow_null=True, required=False
    )
    allowed_roles = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    denied_roles = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    allowed_channels = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    denied_channels = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    allowed_users = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    denied_users = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    cooldown_type = serializers.ChoiceField(
        choices=["user", "channel", "guild"], default="user"
    )
    cooldown_seconds = serializers.IntegerField(default=5, min_value=0, max_value=86400)
    no_permission_message = serializers.CharField(
        default="У вас недостаточно прав для использования этой команды."
    )
