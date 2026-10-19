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
