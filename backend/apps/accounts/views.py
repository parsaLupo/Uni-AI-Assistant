"""Auth endpoints: register, login, refresh, logout, me, admin users.

Contract: `docs/api/auth.md` + the users section of `docs/api/admin.md`.
Policy: ADR-014 (email identity, student-only self-registration, rotation with
reuse detection, double-submit CSRF, rate limits).

User-facing text is Persian; codes and field names stay English (ADR-010).
"""

from __future__ import annotations

import logging

from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts import tokens
from apps.accounts.csrf import enforce_double_submit_csrf
from apps.accounts.models import Role, User
from apps.accounts.permissions import IsAdmin, IsSuperAdmin
from apps.accounts.serializers import (
    DUPLICATE_EMAIL_MESSAGE,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    LoginSerializer,
    LoginUserSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    RegisterSerializer,
)
from apps.accounts.throttles import RefreshRateThrottle
from apps.common.errors import AUTHENTICATION_REQUIRED, CONFLICT, VALIDATION_ERROR, ApiError

logger = logging.getLogger("app.auth")

# Persian messages for the auth flows (docs/api/auth.md).
INVALID_CREDENTIALS_MESSAGE = "ایمیل یا گذرواژه نامعتبر است."
INACTIVE_ACCOUNT_MESSAGE = "حساب کاربری غیرفعال شده است."
SESSION_EXPIRED_MESSAGE = "نشست شما منقضی شده است؛ لطفاً دوباره وارد شوید."
SELF_DEACTIVATE_MESSAGE = "نمی‌توانید حساب خود را غیرفعال کنید."


def _auth_error(message: str) -> ApiError:
    return ApiError(AUTHENTICATION_REQUIRED, message, http_status=401)


def _ensure_can_assign_role(actor: User, new_role: str) -> None:
    """Privileged roles are granted only by a SUPERADMIN (docs/api/admin.md)."""
    if new_role in Role.privileged() and actor.role != Role.SUPERADMIN:
        raise PermissionDenied(IsSuperAdmin.message)


def _ensure_can_deactivate(actor: User, target: User) -> None:
    if target == actor:
        raise ApiError(CONFLICT, SELF_DEACTIVATE_MESSAGE, http_status=409)
    if target.is_privileged and actor.role != Role.SUPERADMIN:
        raise PermissionDenied(IsSuperAdmin.message)


def _tokens_response(
    user: User,
    http_status: int = status.HTTP_200_OK,
    issued: tuple[str, str] | None = None,
) -> Response:
    """Issue tokens, attach both cookies, and return the documented payload.

    ``rotate_refresh`` already issues the rotated pair inside its transaction;
    passing ``issued`` reuses it instead of minting a second family (a replay
    of the old token must revoke the *current* session, not a stranger's).
    """
    access, refresh = issued or tokens.issue_tokens(user)
    response = Response(
        {"access": access, "user": LoginUserSerializer(user).data},
        status=http_status,
    )
    tokens.set_refresh_cookie(response, refresh)
    return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RegisterView(APIView):
    """POST /api/v1/auth/register/ — public, always creates role STUDENT."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_ip"

    @extend_schema(tags=["auth"], request=RegisterSerializer, responses={201: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            # Role is never read from the payload: a client-sent "role" field is
            # ignored because the serializer does not declare it (ADR-014 decision 2).
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                role=Role.STUDENT,
            )
        except IntegrityError:
            # Unique race on email between the serializer check and the insert.
            raise ApiError(CONFLICT, DUPLICATE_EMAIL_MESSAGE, http_status=409) from None
        return _tokens_response(user, http_status=status.HTTP_201_CREATED)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(APIView):
    """POST /api/v1/auth/login/ — email + password (ADR-014 decision 1)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_ip"

    @extend_schema(tags=["auth"], request=LoginSerializer, responses={200: dict})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            # One message for unknown-email and wrong-password: no user oracle.
            raise _auth_error(INVALID_CREDENTIALS_MESSAGE)
        if not user.is_active:
            raise _auth_error(INACTIVE_ACCOUNT_MESSAGE)
        return _tokens_response(user)


class RefreshView(APIView):
    """POST /api/v1/auth/refresh/ — CSRF-protected, rotating (ADR-014)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [RefreshRateThrottle]

    @extend_schema(tags=["auth"], request=None, responses={200: dict})
    def post(self, request):
        enforce_double_submit_csrf(request)
        result = tokens.rotate_refresh(
            request.COOKIES.get(tokens.REFRESH_COOKIE_NAME),
            request_id=getattr(request, "request_id", "-"),
        )
        if result.outcome == tokens.ROTATED:
            assert result.access and result.refresh  # rotate issues both
            return _tokens_response(result.user, issued=(result.access, result.refresh))
        if result.outcome == tokens.INACTIVE:
            raise _auth_error(INACTIVE_ACCOUNT_MESSAGE)
        # missing / invalid / replayed all end the session; the replay branch has
        # already logged the security event and revoked the family.
        raise _auth_error(SESSION_EXPIRED_MESSAGE)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — revoke family + clear cookie, idempotent."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_ip"

    @extend_schema(tags=["auth"], request=None, responses={204: None})
    def post(self, request):
        enforce_double_submit_csrf(request)
        tokens.revoke_family_for(request.COOKIES.get(tokens.REFRESH_COOKIE_NAME))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        tokens.delete_refresh_cookie(response)
        return response


class MeView(APIView):
    """GET /api/v1/auth/me/ — who the Bearer token belongs to."""

    @extend_schema(tags=["auth"], responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)


PASSWORD_CHANGED_MESSAGE = "گذرواژه با موفقیت تغییر کرد."
WRONG_CURRENT_PASSWORD_MESSAGE = "گذرواژهٔ فعلی نادرست است."


class PasswordChangeView(APIView):
    """POST /api/v1/auth/password-change/ — self-service password change.

    Available to every signed-in role (the student's only permitted self
    change). The current password must be re-entered; Django's validators
    guard the new one. The presented refresh-token family is revoked so a
    stolen refresh token cannot outlive the credential change — the caller
    keeps their short-lived access token and re-logs in afterwards.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], request=PasswordChangeSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            raise ApiError(VALIDATION_ERROR, WRONG_CURRENT_PASSWORD_MESSAGE, http_status=400)
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        tokens.revoke_family_for(request.COOKIES.get(tokens.REFRESH_COOKIE_NAME))
        response = Response({"detail": PASSWORD_CHANGED_MESSAGE})
        tokens.delete_refresh_cookie(response)
        return response


class AdminUserListCreateView(ListCreateAPIView):
    """GET/POST /api/v1/admin/users/ — ADMIN+ (docs/api/admin.md)."""

    permission_classes = [IsAdmin]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminUserCreateSerializer
        return MeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        search = params.get("search")
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        role = params.get("role")
        if role in Role.values:
            queryset = queryset.filter(role=role)
        is_active = params.get("is_active")
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset

    @extend_schema(request=AdminUserCreateSerializer, responses={201: MeSerializer})
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        actor = self.request.user
        # Creating an ADMIN/SUPERADMIN account is a SUPERADMIN-only action.
        _ensure_can_assign_role(actor, serializer.validated_data.get("role", Role.STUDENT))
        serializer.save()


class AdminUserDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/admin/users/{id}/ — soft delete = deactivate."""

    permission_classes = [IsAdmin]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return AdminUserUpdateSerializer
        return MeSerializer

    @extend_schema(request=AdminUserUpdateSerializer, responses=MeSerializer)
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def perform_update(self, serializer):
        actor = self.request.user
        target = serializer.instance
        changes = serializer.validated_data
        if "role" in changes and changes["role"] != target.role:
            _ensure_can_assign_role(actor, changes["role"])
            # Altering an existing privileged account is also SUPERADMIN-only.
            if target.is_privileged and actor.role != Role.SUPERADMIN:
                raise PermissionDenied(IsSuperAdmin.message)
        if "is_active" in changes and not changes["is_active"]:
            _ensure_can_deactivate(actor, target)
        serializer.save()

    def perform_destroy(self, instance):
        """DELETE deactivates instead of dropping the row (docs/api/admin.md)."""
        _ensure_can_deactivate(self.request.user, instance)
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

