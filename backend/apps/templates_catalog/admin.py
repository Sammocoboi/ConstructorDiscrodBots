from django.contrib import admin

from .models import Template, TemplateVersion


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "visibility", "is_system", "author", "popularity", "created_at")
    list_filter = ("is_system", "visibility", "category")
    search_fields = ("title", "description", "author__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = ("template", "version", "created_at")
    search_fields = ("template__title", "version")
    readonly_fields = ("id", "created_at", "updated_at")
