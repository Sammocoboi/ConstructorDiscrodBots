"""URLs for commands application"""

from django.urls import path
from backend.apps.commands.views import (
    CommandLibraryListView,
    CommandLibraryDetailView,
    CommandCategoriesView,
    BotInstallCommandsView,
    BotCommandPermissionsView,
)

urlpatterns = [
    path("commands-library", CommandLibraryListView.as_view(), name="commands-library-list"),
    path("commands-library/categories", CommandCategoriesView.as_view(), name="commands-library-categories"),
    path("commands-library/<slug:slug>", CommandLibraryDetailView.as_view(), name="commands-library-detail"),
    path("bots/<uuid:bot_id>/commands/install", BotInstallCommandsView.as_view(), name="bot-commands-install"),
    path(
        "bots/<uuid:bot_id>/commands/<str:command_name>/permissions",
        BotCommandPermissionsView.as_view(),
        name="bot-command-permissions"
    ),
]
