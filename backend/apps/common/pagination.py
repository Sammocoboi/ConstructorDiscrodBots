"""Cursor pagination used by all list endpoints."""

from __future__ import annotations

from rest_framework.pagination import CursorPagination as DRFCursorPagination


class CursorPagination(DRFCursorPagination):
    page_size = 20
    max_page_size = 100
    page_size_query_param = "limit"
    ordering = "-created_at"
