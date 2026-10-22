"""Idempotency-Key для аутентифицированных изменяющих запросов.

Контракт: docs/api-contract.md, ADR-0006. Запрос с заголовком Idempotency-Key
выполняется один раз; повтор с тем же телом получает сохранённый ответ.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from .models import IdempotencyKey

logger = logging.getLogger(__name__)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_BODY_BYTES = 2 * 1024 * 1024


def _error(
    request,
    status: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JsonResponse:
    return JsonResponse(
        {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": getattr(request, "request_id", ""),
        },
        status=status,
    )


class IdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header_name = settings.IDEMPOTENCY_HEADER
        key = request.headers.get(header_name, "").strip()
        if (
            not key
            or request.method not in UNSAFE_METHODS
            or not request.path.startswith("/api/v1/")
        ):
            return self.get_response(request)

        if len(key) > 255:
            return _error(
                request,
                400,
                "invalid_idempotency_key",
                f"{header_name} must be 255 characters or fewer",
            )

        if "multipart/form-data" in (request.content_type or ""):
            # Файлы не буферизуем: для загрузок идемпотентность не поддерживается.
            return self.get_response(request)

        body = request.body or b""
        if len(body) > MAX_BODY_BYTES:
            return _error(
                request,
                413,
                "idempotency_payload_too_large",
                "Request body is too large for idempotent processing",
            )

        user = self._authenticate(request)
        if user is None:
            # Неаутентифицированные запросы обрабатываются обычным путём (401 и т.п.).
            return self.get_response(request)

        fingerprint = self._fingerprint(request, body)
        record = self._find_record(user, key)
        if record is not None:
            replay = self._handle_existing(request, record, fingerprint)
            if replay is not None:
                return replay

        try:
            record = IdempotencyKey.objects.create(
                user=user,
                key=key,
                request_method=request.method,
                request_path=request.path[:500],
                request_hash=fingerprint,
                expires_at=timezone.now() + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
            )
        except IntegrityError:
            # Параллельный запрос успел создать запись между SELECT и INSERT.
            record = self._find_record(user, key)
            if record is None:
                return self.get_response(request)
            replay = self._handle_existing(request, record, fingerprint)
            if replay is not None:
                return replay

        response = self.get_response(request)
        self._store_response(record, response)
        return response

    def _authenticate(self, request):
        try:
            result = JWTAuthentication().authenticate(request)
        except (AuthenticationFailed, InvalidToken):
            return None
        return result[0] if result else None

    @staticmethod
    def _fingerprint(request, body: bytes) -> str:
        query = request.META.get("QUERY_STRING", "")
        payload = b"\n".join(
            (
                request.method.encode("utf-8"),
                request.path.encode("utf-8"),
                query.encode("utf-8"),
                body,
            )
        )
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _find_record(user, key: str) -> IdempotencyKey | None:
        record = IdempotencyKey.objects.filter(user=user, key=key).first()
        if record is not None and record.expires_at <= timezone.now():
            record.delete()
            return None
        return record

    def _handle_existing(
        self, request, record: IdempotencyKey, fingerprint: str
    ) -> HttpResponse | None:
        if record.request_hash != fingerprint:
            return _error(
                request,
                409,
                "idempotency_conflict",
                "This Idempotency-Key was already used with a different request",
                {"key": record.key},
            )
        if record.response_status is None:
            return _error(
                request,
                409,
                "idempotency_in_progress",
                "A request with this Idempotency-Key is still being processed",
                {"key": record.key},
            )
        return self._replay(request, record)

    @staticmethod
    def _replay(request, record: IdempotencyKey) -> HttpResponse:
        if record.response_status in {204, 304}:
            response = HttpResponse(status=record.response_status)
        else:
            response = JsonResponse(
                record.response_body,
                status=record.response_status,
                safe=False,
            )
        response["Idempotent-Replayed"] = "true"
        response["X-Request-ID"] = getattr(request, "request_id", "")
        return response

    @staticmethod
    def _store_response(record: IdempotencyKey, response) -> None:
        if (
            getattr(response, "streaming", False)
            or response.status_code >= 500
            or 300 <= response.status_code < 400
        ):
            # 5xx не кешируем: клиент может повторить запрос с тем же ключом.
            # 3xx (например, APPEND_SLASH) тоже не фиксируем.
            record.delete()
            return

        fields = {
            "response_status": response.status_code,
            "updated_at": timezone.now(),
        }
        content_type = response.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                fields["response_body"] = json.loads(response.content or b"{}")
            except (TypeError, ValueError):
                fields["response_body"] = {}
        IdempotencyKey.objects.filter(pk=record.pk).update(**fields)
