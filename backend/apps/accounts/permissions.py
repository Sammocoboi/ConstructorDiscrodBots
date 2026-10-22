"""Проверки доступных способов входа (замечание заказчика CF-03)."""

from __future__ import annotations

from django.conf import settings
from rest_framework.exceptions import APIException


class AuthMethodDisabled(APIException):
    """Способ входа отключён настройкой ``AUTH_METHODS``."""

    status_code = 403
    default_code = "auth_method_disabled"
    default_detail = "Этот способ входа отключён. Используйте вход через Discord."

    def __init__(self, method: str = "email"):
        super().__init__(
            {
                "detail": f"Вход через {method} отключён. Используйте вход через Discord.",
                "method": method,
            }
        )


def auth_methods() -> set[str]:
    """Возвращает нормализованный набор включённых способов входа."""
    configured = getattr(settings, "AUTH_METHODS", ("email", "discord"))
    if isinstance(configured, str):
        configured = configured.split(",")
    return {str(method).strip().lower() for method in configured if str(method).strip()}


def email_auth_enabled() -> bool:
    """Включён ли вход по email и паролю."""
    return "email" in auth_methods()


class EmailAuthMixin:
    # Блокирует email-эндпоинты, если в AUTH_METHODS оставлен только Discord.
    # Проверка идёт после super().initial(), поэтому throttling и остальные
    # стандартные проверки DRF продолжают работать.

    def initial(self, request, *args, **kwargs) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        if not email_auth_enabled():
            raise AuthMethodDisabled("email")
