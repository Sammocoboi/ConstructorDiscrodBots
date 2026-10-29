from rest_framework import serializers

from .models import Module


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = (
            "id",
            "slug",
            "title",
            "description",
            "manifest",
            "settings_schema",
            "is_premium",
            "min_plan",
            "is_active",
        )
        read_only_fields = fields


class UpdateModuleSettingsSerializer(serializers.Serializer):
    guild_id = serializers.CharField(required=True)
    enabled = serializers.BooleanField(required=True)
    settings = serializers.DictField(required=False, default=dict)
    bot_permissions = serializers.IntegerField(required=False, default=0)
    bot_highest_role_pos = serializers.IntegerField(required=False, default=100)
    target_role_pos = serializers.IntegerField(required=False, allow_null=True, default=None)
