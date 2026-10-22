from django.contrib import admin

from .models import IdempotencyKey, PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "site_name",
        "support_email",
        "maintenance_mode",
        "registration_enabled",
        "trial_days",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "request_method", "response_status", "expires_at")
    list_filter = ("request_method", "response_status")
    search_fields = ("user__email", "key", "request_path")
    readonly_fields = (
        "id",
        "user",
        "key",
        "request_method",
        "request_path",
        "request_hash",
        "response_status",
        "response_body",
        "expires_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
