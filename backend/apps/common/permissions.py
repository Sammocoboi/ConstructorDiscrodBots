"""Shared object-level permissions."""

from __future__ import annotations

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Allow access only to the owner of an object."""

    owner_field = "owner"

    def has_object_permission(self, request, view, obj):
        return getattr(obj, self.owner_field, None) == request.user


class IsOwnerOrReadOnly(IsOwner):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return super().has_object_permission(request, view, obj)


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Read-only for everyone, writes only for the object's author."""

    author_field = "author"

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, self.author_field, None) == request.user
