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
