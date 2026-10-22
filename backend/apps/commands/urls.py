from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BotCommandPermissionsView,
    BotInstallCommandsView,
    CommandCategoriesView,
    CommandLibraryViewSet,
)

router = DefaultRouter()
router.register("commands-library", CommandLibraryViewSet, basename="command-library")

urlpatterns = [
    path(
        "commands-library/categories",
        CommandCategoriesView.as_view(),
        name="commands-library-categories",
    ),
    path(
        "bots/<uuid:bot_id>/commands/install",
        BotInstallCommandsView.as_view(),
        name="bot-commands-install",
    ),
    path(
        "bots/<uuid:bot_id>/commands/<str:command_name>/permissions",
        BotCommandPermissionsView.as_view(),
        name="bot-command-permissions",
    ),
    *router.urls,
]
