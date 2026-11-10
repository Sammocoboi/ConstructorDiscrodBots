from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .guild_resources import BotGuildResourcesView
from .flow_views import BotFlowActionView, BotFlowDetailView, BotFlowListCreateView

router = DefaultRouter()
router.register("bots", views.BotViewSet, basename="bot")

urlpatterns = [
    path(
        "bots/<uuid:bot_id>/guilds/<str:guild_id>/resources",
        BotGuildResourcesView.as_view(),
        name="bot-guild-resources",
    ),
    path(
        "bots/<uuid:bot_id>/flows",
        BotFlowListCreateView.as_view(),
        name="bot-flow-list-create",
    ),
    path(
        "bots/<uuid:bot_id>/flows/<uuid:flow_id>",
        BotFlowDetailView.as_view(),
        name="bot-flow-detail",
    ),
    path(
        "bots/<uuid:bot_id>/flows/<uuid:flow_id>/<str:action>",
        BotFlowActionView.as_view(),
        name="bot-flow-action",
    ),
    path(
        "bots/<uuid:bot_id>/guilds/sync",
        views.BotGuildSyncView.as_view(),
        name="bot-guild-sync",
    ),
    path(
        "bots/validate-token",
        views.ValidateTokenView.as_view(),
        name="bot-validate-token",
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
