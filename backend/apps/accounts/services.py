"""Authentication services: tokens, cookies, email links, Discord OAuth."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.crypto import encrypt_secret
from apps.common.utils import get_client_ip

from .models import OAuthAccount, RefreshSession, User

logger = logging.getLogger(__name__)

EMAIL_VERIFY_SALT = "email-verify"
PASSWORD_RESET_SALT = "password-reset"


class DiscordOAuthError(Exception):
    """Raised when Discord OAuth exchange or profile request fails."""


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_from_refresh(user: User, refresh: RefreshToken, request=None) -> RefreshSession:
    expires_at = datetime.fromtimestamp(refresh["exp"], tz=dt_timezone.utc)
    return RefreshSession.objects.create(
        user=user,
        jti=refresh["jti"],
        token_hash=hash_token(str(refresh)),
        device_info=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
        ip=get_client_ip(request) if request else None,
        expires_at=expires_at,
    )


def issue_tokens(user: User, request=None) -> dict:
    refresh = RefreshToken.for_user(user)
    session = _session_from_refresh(user, refresh, request)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "session": session,
    }


def rotate_refresh_token(raw_token: str, request=None) -> dict:
    try:
        token = RefreshToken(raw_token)
    except Exception as exc:
        raise InvalidToken("Invalid or expired refresh token") from exc

    session = RefreshSession.objects.filter(
        jti=token["jti"], revoked_at__isnull=True
    ).first()
    if session is None:
        raise InvalidToken("Session is revoked")

    try:
        user = User.objects.get(id=token["user_id"])
    except User.DoesNotExist as exc:
        raise InvalidToken("User not found") from exc

    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at", "updated_at"])
    try:
        token.blacklist()
    except Exception:  # pragma: no cover - blacklist app may be unavailable
        logger.warning("Could not blacklist refresh token", exc_info=True)

    return issue_tokens(user, request)


def revoke_session(user: User, jti: str) -> bool:
    updated = RefreshSession.objects.filter(
        user=user, jti=jti, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())
    return bool(updated)


def revoke_all_sessions(user: User) -> int:
    return RefreshSession.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def set_refresh_cookie(response, refresh_token: str) -> None:
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


# ---------------------------------------------------------------------------
# Email tokens
# ---------------------------------------------------------------------------
def make_email_verify_token(user: User) -> str:
    return signing.TimestampSigner(salt=EMAIL_VERIFY_SALT).sign(str(user.id))


def verify_email_token(token: str) -> User:
    try:
        user_id = signing.TimestampSigner(salt=EMAIL_VERIFY_SALT).unsign(
            token, max_age=24 * 60 * 60
        )
    except signing.BadSignature as exc:
        raise ValueError("Invalid or expired email verification token") from exc
    return User.objects.get(id=user_id)


def make_password_reset_token(user: User) -> str:
    return signing.TimestampSigner(salt=PASSWORD_RESET_SALT).sign(str(user.id))


def verify_password_reset_token(token: str) -> User:
    try:
        user_id = signing.TimestampSigner(salt=PASSWORD_RESET_SALT).unsign(
            token, max_age=60 * 60
        )
    except signing.BadSignature as exc:
        raise ValueError("Invalid or expired password reset token") from exc
    return User.objects.get(id=user_id)


def send_email_verification(user: User) -> None:
    token = make_email_verify_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    send_mail(
        subject="Подтвердите email — Constructor Discord Bots",
        message=f"Здравствуйте, {user.display_name}!\n\nПодтвердите email по ссылке:\n{link}\n\nСсылка действует 24 часа.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset(user: User) -> None:
    token = make_password_reset_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    send_mail(
        subject="Сброс пароля — Constructor Discord Bots",
        message=(
            f"Здравствуйте, {user.display_name}!\n\n"
            f"Сбросить пароль можно по ссылке:\n{link}\n\n"
            "Ссылка действует 1 час. Если вы не запрашивали сброс, просто проигнорируйте письмо."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


# ---------------------------------------------------------------------------
# Discord OAuth2
# ---------------------------------------------------------------------------
def build_discord_authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "redirect_uri": settings.DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(settings.DISCORD_OAUTH_SCOPES),
            "state": state,
            "prompt": "consent",
        }
    )
    return f"https://discord.com/oauth2/authorize?{query}"


def exchange_discord_code(code: str) -> dict:
    if not settings.DISCORD_CLIENT_ID or not settings.DISCORD_CLIENT_SECRET:
        raise DiscordOAuthError("Discord OAuth is not configured")
    try:
        response = requests.post(
            f"{settings.DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise DiscordOAuthError("Discord token endpoint is unavailable") from exc
    if response.status_code >= 400:
        logger.warning("Discord token exchange failed: %s %s", response.status_code, response.text)
        raise DiscordOAuthError("Discord rejected the authorization code")
    return response.json()


def fetch_discord_user(access_token: str) -> dict:
    try:
        response = requests.get(
            f"{settings.DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise DiscordOAuthError("Discord API is unavailable") from exc
    if response.status_code >= 400:
        raise DiscordOAuthError("Could not fetch Discord profile")
    return response.json()


def _discord_avatar_url(discord_user: dict) -> str:
    user_id = discord_user.get("id", "")
    avatar = discord_user.get("avatar")
    if not avatar:
        return ""
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=256"


def get_or_create_discord_user(discord_user: dict, token_data: dict) -> User:
    provider_user_id = str(discord_user["id"])
    oauth = OAuthAccount.all_objects.filter(
        provider=OAuthAccount.Provider.DISCORD,
        provider_user_id=provider_user_id,
    ).first()

    if oauth is not None:
        user = oauth.user
        if user.deleted_at is not None:
            raise DiscordOAuthError("Account is deleted")
    else:
        email = (discord_user.get("email") or "").lower()
        user = User.all_objects.filter(email=email).first() if email else None
        if user is None:
            fallback_email = email or f"discord_{provider_user_id}@users.noreply.local"
            user = User.objects.create_user(
                email=fallback_email,
                password=None,
                display_name=(
                    discord_user.get("global_name")
                    or discord_user.get("username")
                    or f"Discord {provider_user_id}"
                ),
                avatar_url=_discord_avatar_url(discord_user),
            )
        oauth = OAuthAccount(
            user=user,
            provider=OAuthAccount.Provider.DISCORD,
            provider_user_id=provider_user_id,
        )

    if discord_user.get("email"):
        user.email = discord_user["email"].lower()
        if user.email_verified_at is None and discord_user.get("verified", True):
            user.email_verified_at = timezone.now()
    if discord_user.get("global_name") or discord_user.get("username"):
        user.display_name = discord_user.get("global_name") or discord_user.get("username")
    user.avatar_url = _discord_avatar_url(discord_user) or user.avatar_url
    user.save()

    oauth.access_token_encrypted = encrypt_secret(token_data.get("access_token", ""))
    oauth.refresh_token_encrypted = encrypt_secret(token_data.get("refresh_token", ""))
    oauth.scopes = token_data.get("scope", "").split()
    expires_in = token_data.get("expires_in")
    oauth.expires_at = (
        timezone.now() + timedelta(seconds=int(expires_in)) if expires_in else None
    )
    oauth.save()
    return user


def create_discord_login_code(user: User) -> str:
    code = secrets.token_urlsafe(32)
    cache.set(f"discord:login:{code}", str(user.id), timeout=settings.DISCORD_LOGIN_CODE_TTL)
    return code


def consume_discord_login_code(code: str) -> User | None:
    user_id = cache.get(f"discord:login:{code}")
    if not user_id:
        return None
    cache.delete(f"discord:login:{code}")
    return User.objects.filter(id=user_id).first()


def build_discord_state() -> str:
    state = secrets.token_urlsafe(32)
    cache.set(f"discord:state:{state}", True, timeout=settings.DISCORD_OAUTH_STATE_TTL)
    return state


def consume_discord_state(state: str) -> bool:
    if not state or not cache.get(f"discord:state:{state}"):
        return False
    cache.delete(f"discord:state:{state}")
    return True


def discord_callback_redirect(code: str | None = None, error: str | None = None) -> str:
    frontend = f"{settings.FRONTEND_URL}/auth/callback"
    if error:
        return f"{frontend}?{urlencode({'error': error})}"
    return f"{frontend}?{urlencode({'code': code or ''})}"
