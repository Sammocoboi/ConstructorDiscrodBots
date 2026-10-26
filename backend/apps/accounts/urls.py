from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="register"),
    path("login", views.LoginView.as_view(), name="login"),
    path("refresh", views.RefreshView.as_view(), name="refresh"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("logout-all", views.LogoutAllView.as_view(), name="logout-all"),
    path("csrf", views.CsrfView.as_view(), name="csrf"),
    path("health", views.HealthView.as_view(), name="health"),
    path("me", views.MeView.as_view(), name="me"),
    path("me/sessions", views.SessionListView.as_view(), name="sessions"),
    path(
        "me/sessions/<uuid:session_id>",
        views.SessionDetailView.as_view(),
        name="session-detail",
    ),
    path("me/discord-guilds", views.UserDiscordGuildsView.as_view(), name="discord-guilds"),
    path("discord/login", views.DiscordLoginView.as_view(), name="discord-login"),
    path("discord/callback", views.DiscordCallbackView.as_view(), name="discord-callback"),
    path("discord/exchange", views.DiscordExchangeView.as_view(), name="discord-exchange"),
    path("email/verify", views.EmailVerifyView.as_view(), name="email-verify"),
    path(
        "password/reset/request",
        views.PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/confirm",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
