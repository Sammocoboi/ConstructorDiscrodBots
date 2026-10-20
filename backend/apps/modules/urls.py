
from django.urls import path
from backend.apps.modules.views import (
    ModuleListView,
    ModuleDetailView,
    BotModulesView,
    BotModuleUpdateView,
)

urlpatterns = [
    path("modules", ModuleListView.as_view(), name="modules-list"),
    path("modules/<slug:slug>", ModuleDetailView.as_view(), name="modules-detail"),
    path("bots/<uuid:bot_id>/modules", BotModulesView.as_view(), name="bot-modules-list"),
    path("bots/<uuid:bot_id>/modules/<slug:slug>", BotModuleUpdateView.as_view(), name="bot-module-update"),
]
