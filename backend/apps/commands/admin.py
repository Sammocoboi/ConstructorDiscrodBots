from django.contrib import admin

from .models import CommandLibrary


@admin.register(CommandLibrary)
class CommandLibraryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "category", "type", "popularity", "is_active")
    list_filter = ("category", "type", "is_active")
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
