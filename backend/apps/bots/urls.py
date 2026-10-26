from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("bots", views.BotViewSet, basename="bot")

urlpatterns = [
    path(
        "bots/<uuid:bot_id>/guilds/sync",
        views.BotGuildSyncView.as_view(),
        name="bot-guild-sync",
    ),
    path(
        "bots/<uuid:bot_id>/guilds/<str:guild_id>",
        views.BotGuildDetailView.as_view(),
        name="bot-guild-detail",
    ),
    path(
        "bots/<uuid:bot_id>/versions/<uuid:version_id>",
        views.BotVersionDetailView.as_view(),
        name="bot-version-detail",
    ),
] + router.urls
