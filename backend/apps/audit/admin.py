from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id", "ip")
    list_filter = ("action", "object_type")
    search_fields = ("actor__email", "action", "object_type", "object_id")
    readonly_fields = (
        "id",
        "actor",
        "action",
        "object_type",
        "object_id",
        "ip",
        "user_agent",
        "diff",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
