"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/v1/auth/", include("apps.accounts.urls")),
    # Удобные алиасы из ТЗ: /me, /me/sessions, /health.
    path("api/v1/me", account_views.MeView.as_view(), name="me"),
    path("api/v1/me/sessions", account_views.SessionListView.as_view(), name="sessions"),
    path(
        "api/v1/me/sessions/<uuid:session_id>",
        account_views.SessionDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "api/v1/me/discord-guilds",
        account_views.UserDiscordGuildsView.as_view(),
        name="me-discord-guilds",
    ),
    path("api/v1/health", account_views.HealthView.as_view(), name="health"),
    path("api/v1/", include("apps.bots.urls")),
    path("api/v1/", include("apps.templates_catalog.urls")),
    path("api/v1/", include("apps.modules.urls")),
    path("api/v1/", include("apps.commands.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/v1/", include("apps.notifications.urls")),
]
