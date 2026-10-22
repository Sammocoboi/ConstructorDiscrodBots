"""Unified API error format."""

from __future__ import annotations

from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class LimitExceeded(APIException):
    """Тарифный лимит исчерпан (FR-4.10)."""

    status_code = 403
    default_code = "limit_exceeded"

    def __init__(self, limit: str, message: str | None = None):
        self.limit = limit
        super().__init__(
            {
                "detail": message or f"Plan limit exceeded: {limit}",
                "limit": limit,
            }
        )


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    request = context.get("request")
    request_id = getattr(request, "request_id", "")
    data = response.data

    code = getattr(exc, "default_code", "error")
    message = "Request failed"
    details: dict | list = {}

    if isinstance(data, dict) and "detail" in data:
        message = str(data["detail"])
        details = {key: value for key, value in data.items() if key != "detail"}
    elif isinstance(data, dict):
        message = "Validation error"
        details = data
        code = "validation_error"
    elif isinstance(data, list):
        message = "Validation error"
        details = {"non_field_errors": data}
        code = "validation_error"
    else:
        message = str(data)

    response.data = {
        "code": code,
        "message": message,
        "details": details,
        "request_id": request_id,
    }
    return response
