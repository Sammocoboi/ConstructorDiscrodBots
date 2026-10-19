from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "read_at", "created_at")
    list_filter = ("type", "read_at")
    search_fields = ("user__email", "type")
    readonly_fields = ("id", "created_at", "updated_at")
