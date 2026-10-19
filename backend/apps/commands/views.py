from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import CommandLibrary
from .serializers import CommandLibraryListSerializer, CommandLibrarySerializer


class CommandLibraryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = CommandLibrary.objects.filter(is_active=True)
    filterset_fields = ("category", "type", "is_active")
    search_fields = ("title", "description", "slug")
    ordering_fields = ("title", "popularity", "category")

    def get_serializer_class(self):
        if self.action == "list":
            return CommandLibraryListSerializer
        return CommandLibrarySerializer
