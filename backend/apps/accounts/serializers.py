"""Serializers for accounts and auth."""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from .models import OAuthAccount, RefreshSession, User


class UserSerializer(serializers.ModelSerializer):
    is_email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "display_name",
            "avatar_url",
            "locale",
            "timezone",
            "is_staff",
            "is_email_verified",
            "email_verified_at",
            "created_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        value = value.lower().strip()
        if User.all_objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data):
        display_name = validated_data.get("display_name") or validated_data["email"].split("@")[0]
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            display_name=display_name,
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(
            request=request,
            email=attrs["email"].lower().strip(),
            password=attrs["password"],
        )
        if user is None:
            raise AuthenticationFailed("Неверный email или пароль")
        if not user.is_active:
            raise AuthenticationFailed("Аккаунт отключён")
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("display_name", "avatar_url", "locale", "timezone")


class RefreshSessionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = RefreshSession
        fields = (
            "id",
            "device_info",
            "ip",
            "created_at",
            "expires_at",
            "revoked_at",
            "is_active",
        )
        read_only_fields = fields


class OAuthAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = OAuthAccount
        fields = ("provider", "provider_user_id", "scopes", "expires_at", "created_at")
        read_only_fields = fields


class DiscordExchangeSerializer(serializers.Serializer):
    code = serializers.CharField()


class EmailVerifySerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class EmptySerializer(serializers.Serializer):
    pass
