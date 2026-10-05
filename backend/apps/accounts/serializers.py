"""Serializer contract for the auth endpoints (docs/api/auth.md, ADR-014)."""

from __future__ import annotations

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.common.errors import CONFLICT, ApiError

DUPLICATE_EMAIL_MESSAGE = "کاربری با این ایمیل قبلاً ثبت شده است."


def normalize_email(value: str) -> str:
    """One normalization for register, login and admin create (ADR-014)."""
    return value.strip().lower()


def validate_password_value(value: str) -> str:
    """Run Django's validators; surface failures as Persian field errors."""
    try:
        password_validation.validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class LoginUserSerializer(serializers.Serializer):
    """Minimal user summary returned by login/register/refresh (docs/api/auth.md)."""

    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.ChoiceField(choices=Role.choices, read_only=True)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active")
        read_only_fields = ("id", "email", "role", "is_active")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        email = normalize_email(value)
        if User.objects.filter(email=email).exists():
            raise ApiError(CONFLICT, DUPLICATE_EMAIL_MESSAGE, http_status=409)
        return email

    def validate_password(self, value: str) -> str:
        return validate_password_value(value)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        return normalize_email(value)


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Admin-provisioned account (ADR-014 decision 2: privileged roles only here)."""

    password = serializers.CharField(write_only=True, trim_whitespace=False)
    # Silence ModelSerializer's generated UniqueValidator: duplicates must reach
    # validate_email so the contract's 409 CONFLICT (not DRF's 400) is returned.
    email = serializers.EmailField(validators=[])

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "role")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        email = normalize_email(value)
        if User.objects.filter(email=email).exists():
            raise ApiError(CONFLICT, DUPLICATE_EMAIL_MESSAGE, http_status=409)
        return email

    def validate_password(self, value: str) -> str:
        return validate_password_value(value)


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Email is immutable; role changes are guarded in the view (see docs/api/admin.md)."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active")
        read_only_fields = ("id", "email")
