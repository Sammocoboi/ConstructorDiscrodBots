"""Request ID middleware: every response gets an X-Request-ID header."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from django.urls import Resolver404, resolve

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = request_id
        return response


class SlashTolerantMiddleware:
    """Route API requests without a trailing slash to the slashed URL.

    Django's ``APPEND_SLASH`` redirects GET/HEAD with a 301 and raises
    ``RuntimeError`` for unsafe methods (POST/PUT/PATCH/DELETE), because a
    redirect would drop the request body. The SPA calls DRF router endpoints
    without the trailing slash, so rewrite the path internally instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path and not path.endswith("/"):
            if not self._resolves(path):
                slashed = f"{path}/"
                if self._resolves(slashed):
                    request.path_info = slashed
                    if request.path.endswith("/") is False:
                        request.path = f"{request.path}/"
        return self.get_response(request)

    @staticmethod
    def _resolves(path: str) -> bool:
        try:
            resolve(path)
        except Resolver404:
            return False
        return True
