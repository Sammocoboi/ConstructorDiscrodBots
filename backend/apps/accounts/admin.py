from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OAuthAccount, RefreshSession, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)
    list_display = (
        "email",
        "display_name",
        "locale",
        "is_active",
        "is_staff",
        "email_verified_at",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "locale", "deleted_at")
    search_fields = ("email", "display_name")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "deleted_at")
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (
            "Профиль",
            {"fields": ("display_name", "avatar_url", "locale", "timezone", "email_verified_at")},
        ),
        (
            "Права",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Служебное", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2", "is_staff"),
            },
        ),
    )


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    list_display = ("provider", "provider_user_id", "user", "expires_at", "created_at")
    list_filter = ("provider",)
    search_fields = ("provider_user_id", "user__email")
    readonly_fields = (
        "id",
        "access_token_encrypted",
        "refresh_token_encrypted",
        "created_at",
        "updated_at",
        "deleted_at",
    )


@admin.register(RefreshSession)
class RefreshSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "jti", "ip", "created_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__email", "jti", "ip")
    readonly_fields = ("id", "token_hash", "created_at", "updated_at", "deleted_at")
