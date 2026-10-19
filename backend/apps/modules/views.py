from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Module
from .serializers import ModuleSerializer


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    queryset = Module.objects.filter(is_active=True)
    filterset_fields = ("is_premium", "min_plan")
    search_fields = ("title", "description")
    ordering_fields = ("title",)
