"""Authentication and profile endpoints."""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    ValidationError,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.audit.models import AuditLog

from . import services
from .models import RefreshSession, User
from .permissions import EmailAuthMixin
from .serializers import (
    DiscordExchangeSerializer,
    DiscordUserGuildSerializer,
    EmailVerifySerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RefreshSessionSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


def _refresh_token_from_request(request) -> str | None:
    return request.COOKIES.get(settings.REFRESH_COOKIE_NAME) or request.data.get("refresh")


def _audit(action: str, *, user, request, diff: dict | None = None) -> None:
    """Пишет действие в журнал, не ломая основной сценарий при сбое."""
    try:
        AuditLog.record(actor=user, action=action, request=request, diff=diff or {})
    except Exception:  # pragma: no cover - аудит не должен блокировать вход
        logger.exception("Could not write audit log: %s", action)


class RegisterView(EmailAuthMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
            403: OpenApiResponse(description="Email auth disabled (auth_method_disabled)"),
        },
        summary="Регистрация по email и паролю",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _audit("auth.register", user=user, request=request)
        try:
            services.send_email_verification(user)
        except Exception:  # pragma: no cover - email provider failure should not break signup
            logger.exception("Could not send verification email")
        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "Регистрация успешна. Проверьте почту для подтверждения email.",
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(EmailAuthMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Invalid credentials"),
            403: OpenApiResponse(description="Email auth disabled (auth_method_disabled)"),
        },
        summary="Вход по email и паролю",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.last_login = timezone.now()
        user.save(update_fields=["last_login", "updated_at"])
        tokens = services.issue_tokens(user, request)
        _audit("auth.login", user=user, request=request, diff={"method": "password"})
        response = Response(
            {"access": tokens["access"], "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        services.set_refresh_cookie(response, tokens["refresh"])
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token"

    @method_decorator(csrf_protect)
    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="New access token"),
            401: OpenApiResponse(description="Invalid refresh token"),
        },
        summary="Обновить access-токен по refresh-cookie",
    )
    def post(self, request):
        raw_token = _refresh_token_from_request(request)
        if not raw_token:
            raise NotAuthenticated("Refresh token is missing")
        try:
            tokens = services.rotate_refresh_token(raw_token, request)
        except InvalidToken as exc:
            raise AuthenticationFailed("Refresh token is invalid or revoked") from exc
        response = Response({"access": tokens["access"]}, status=status.HTTP_200_OK)
        services.set_refresh_cookie(response, tokens["refresh"])
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect)
    @extend_schema(request=None, responses={204: None}, summary="Выйти из текущей сессии")
    def post(self, request):
        raw_token = _refresh_token_from_request(request)
        if raw_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken

                token = RefreshToken(raw_token)  # type: ignore[arg-type]
                services.revoke_session(request.user, token["jti"])
                token.blacklist()
            except Exception:
                logger.info("Could not blacklist token on logout", exc_info=True)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        services.clear_refresh_cookie(response)
        _audit("auth.logout", user=request.user, request=request)
        return response


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description="Sessions revoked")},
        summary="Выйти на всех устройствах",
    )
    def post(self, request):
        count = services.revoke_all_sessions(request.user)
        response = Response({"revoked_sessions": count}, status=status.HTTP_200_OK)
        services.clear_refresh_cookie(response)
        _audit("auth.logout_all", user=request.user, request=request, diff={"revoked": count})
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer}, summary="Текущий профиль")
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        request=ProfileUpdateSerializer, responses={200: UserSerializer}, summary="Обновить профиль"
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

    @extend_schema(request=None, responses={204: None}, summary="Мягко удалить аккаунт")
    def delete(self, request):
        user = request.user
        services.revoke_all_sessions(user)
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        user.delete()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        services.clear_refresh_cookie(response)
        return response


class UserDiscordGuildsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DiscordUserGuildSerializer(many=True)},
        summary="Серверы пользователя из Discord OAuth (только с правами управления)",
    )
    def get(self, request):
        guilds = services.fetch_user_manageable_guilds(request.user)
        return Response(DiscordUserGuildSerializer(guilds, many=True).data)


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: RefreshSessionSerializer(many=True)}, summary="Активные сессии")
    def get(self, request):
        sessions = RefreshSession.objects.filter(
            user=request.user, revoked_at__isnull=True, expires_at__gt=timezone.now()
        )
        return Response(RefreshSessionSerializer(sessions, many=True).data)


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None}, summary="Отозвать сессию")
    def delete(self, request, session_id):
        session = RefreshSession.objects.filter(
            id=session_id, user=request.user, revoked_at__isnull=True
        ).first()
        if session is None:
            raise NotFound("Session not found")
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class DiscordLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={302: OpenApiResponse(description="Redirect to Discord")},
        summary="Начать вход через Discord",
    )
    def get(self, request):
        state = services.build_discord_state()
        return HttpResponseRedirect(services.build_discord_authorize_url(state))


class DiscordCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={302: OpenApiResponse(description="Redirect to frontend")},
        summary="Callback Discord OAuth2",
    )
    def get(self, request):
        state = request.query_params.get("state", "")
        if not services.consume_discord_state(state):
            return HttpResponseRedirect(services.discord_callback_redirect(error="invalid_state"))
        error = request.query_params.get("error")
        if error:
            return HttpResponseRedirect(services.discord_callback_redirect(error=error))
        code = request.query_params.get("code", "")
        if not code:
            return HttpResponseRedirect(services.discord_callback_redirect(error="missing_code"))
        try:
            token_data = services.exchange_discord_code(code)
            discord_user = services.fetch_discord_user(token_data["access_token"])
            user = services.get_or_create_discord_user(discord_user, token_data)
        except services.DiscordOAuthError:
            logger.exception("Discord OAuth callback failed")
            return HttpResponseRedirect(
                services.discord_callback_redirect(error="discord_oauth_failed")
            )
        login_code = services.create_discord_login_code(user)
        return HttpResponseRedirect(services.discord_callback_redirect(code=login_code))


class DiscordExchangeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token"

    @extend_schema(
        request=DiscordExchangeSerializer,
        responses={200: UserSerializer, 400: OpenApiResponse(description="Invalid code")},
        summary="Обменять одноразовый код на JWT",
    )
    def post(self, request):
        serializer = DiscordExchangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.consume_discord_login_code(serializer.validated_data["code"])
        if user is None:
            raise ValidationError({"code": "Login code is invalid or expired"})
        tokens = services.issue_tokens(user, request)
        _audit("auth.login", user=user, request=request, diff={"method": "discord"})
        response = Response(
            {"access": tokens["access"], "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
        services.set_refresh_cookie(response, tokens["refresh"])
        return response


class EmailVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token"

    @extend_schema(
        request=EmailVerifySerializer, responses={200: UserSerializer}, summary="Подтвердить email"
    )
    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.verify_email_token(serializer.validated_data["token"])
        except (ValueError, User.DoesNotExist) as exc:
            raise ValidationError({"token": "Verification token is invalid or expired"}) from exc
        user.mark_email_verified()
        _audit("auth.email_verified", user=user, request=request)
        return Response(UserSerializer(user).data)


class PasswordResetRequestView(EmailAuthMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            202: None,
            403: OpenApiResponse(description="Email auth disabled (auth_method_disabled)"),
        },
        summary="Запросить сброс пароля",
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"].lower()).first()
        if user is not None:
            try:
                services.send_password_reset(user)
            except Exception:  # pragma: no cover
                logger.exception("Could not send password reset email")
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(EmailAuthMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            204: None,
            403: OpenApiResponse(description="Email auth disabled (auth_method_disabled)"),
        },
        summary="Сбросить пароль",
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.verify_password_reset_token(serializer.validated_data["token"])
        except (ValueError, User.DoesNotExist) as exc:
            raise ValidationError({"token": "Reset token is invalid or expired"}) from exc
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        services.revoke_all_sessions(user)
        _audit("auth.password_reset", user=user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CsrfView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    @extend_schema(request=None, responses={204: None}, summary="Получить CSRF-cookie")
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        responses={200: OpenApiResponse(description="Service is alive")}, summary="Health check"
    )
    def get(self, request):
        return Response({"status": "ok"})
