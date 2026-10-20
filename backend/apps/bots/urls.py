"""URLs for bots application"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from backend.apps.bots.views import (
    BotViewSet,
    BotGuildViewSet,
    UserDiscordGuildsView,
)

router = DefaultRouter()
router.register(r"bots", BotViewSet, basename="bot")

urlpatterns = [
    path("me/discord-guilds", UserDiscordGuildsView.as_view(), name="user-discord-guilds"),
    path(
        "bots/<uuid:bot_pk>/guilds/",
        BotGuildViewSet.as_view({"get": "list", "post": "create"}),
        name="bot-guilds-list"
    ),
    path(
        "bots/<uuid:bot_pk>/guilds/<uuid:pk>/",
        BotGuildViewSet.as_view({"get": "retrieve", "patch": "update_settings", "delete": "destroy"}),
        name="bot-guilds-detail"
    ),
    path(
        "bots/<uuid:bot_pk>/guilds/<uuid:pk>/channels/",
        BotGuildViewSet.as_view({"get": "channels"}),
        name="bot-guilds-channels"
    ),
    path(
        "bots/<uuid:bot_pk>/guilds/<uuid:pk>/roles/",
        BotGuildViewSet.as_view({"get": "roles"}),
        name="bot-guilds-roles"
    ),
    path(
        "bots/<uuid:bot_pk>/guilds/<uuid:pk>/emojis/",
        BotGuildViewSet.as_view({"get": "emojis"}),
        name="bot-guilds-emojis"
    ),
    path("", include(router.urls)),
]
