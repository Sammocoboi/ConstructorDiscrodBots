from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BotModulesView, BotModuleUpdateView, ModuleViewSet

router = DefaultRouter()
router.register("modules", ModuleViewSet, basename="module")

urlpatterns = [
    path(
        "bots/<uuid:bot_id>/modules",
        BotModulesView.as_view(),
        name="bot-modules",
    ),
    path(
        "bots/<uuid:bot_id>/modules/<slug:slug>",
        BotModuleUpdateView.as_view(),
        name="bot-module-update",
    ),
    *router.urls,
]
