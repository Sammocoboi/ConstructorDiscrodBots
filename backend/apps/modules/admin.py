from django.contrib import admin

from .models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_premium", "min_plan", "is_active")
    list_filter = ("is_premium", "min_plan", "is_active")
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
