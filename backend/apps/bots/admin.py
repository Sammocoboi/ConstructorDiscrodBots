from django.contrib import admin

from .models import (
    Bot,
    BotDraft,
    BotGuild,
    BotMember,
    BotRuntimeState,
    BotVariable,
    BotVersion,
    RuntimeCommand,
    ScheduledJob,
)


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "status",
        "desired_state",
        "has_token",
        "created_at",
    )
    list_filter = ("status", "desired_state", "deleted_at")
    search_fields = ("name", "owner__email", "discord_application_id")
    readonly_fields = ("id", "token_encrypted", "created_at", "updated_at", "deleted_at")
    autocomplete_fields = ("owner",)


@admin.register(BotGuild)
class BotGuildAdmin(admin.ModelAdmin):
    list_display = ("guild_name", "guild_id", "bot", "joined_at", "left_at")
    search_fields = ("guild_name", "guild_id", "bot__name")
    list_filter = ("left_at",)


@admin.register(BotVersion)
class BotVersionAdmin(admin.ModelAdmin):
    list_display = ("bot", "version_number", "comment", "published_at")
    search_fields = ("bot__name", "comment")


@admin.register(BotDraft)
class BotDraftAdmin(admin.ModelAdmin):
    list_display = ("bot", "updated_by", "updated_at")


@admin.register(BotVariable)
class BotVariableAdmin(admin.ModelAdmin):
    list_display = ("bot", "scope", "key", "guild_id", "user_discord_id")
    list_filter = ("scope",)
    search_fields = ("bot__name", "key")


@admin.register(RuntimeCommand)
class RuntimeCommandAdmin(admin.ModelAdmin):
    list_display = ("bot", "command", "status", "requested_by", "created_at", "processed_at")
    list_filter = ("command", "status")
    search_fields = ("bot__name",)


@admin.register(BotRuntimeState)
class BotRuntimeStateAdmin(admin.ModelAdmin):
    list_display = ("bot", "status", "worker_id", "latency_ms", "heartbeat_at")
    list_filter = ("status",)
    search_fields = ("bot__name", "worker_id")


@admin.register(ScheduledJob)
class ScheduledJobAdmin(admin.ModelAdmin):
    list_display = ("bot", "flow_id", "run_at", "status", "cron")
    list_filter = ("status",)
    search_fields = ("bot__name", "flow_id")


@admin.register(BotMember)
class BotMemberAdmin(admin.ModelAdmin):
    list_display = ("bot", "user", "role")
    list_filter = ("role",)
    search_fields = ("bot__name", "user__email")
