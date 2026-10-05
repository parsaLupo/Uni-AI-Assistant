"""Refresh-token lifecycle: issue, rotate, revoke, cookie handling (ADR-014).

Rotation with reuse detection (decision 3 of ADR-014): every refresh is recorded;
presenting a revoked one revokes the entire family, which turns token theft into
a loud, immediately-contained event instead of a silent session hijack.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import RefreshTokenRecord, User

logger = logging.getLogger("app.auth")

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
REFRESH_COOKIE_SAMESITE = "Lax"

# Rotation outcomes consumed by the views.
MISSING = "missing"
INVALID = "invalid"
REPLAYED = "replayed"
INACTIVE = "inactive"
ROTATED = "rotated"


@dataclass
class RotationResult:
    outcome: str
    user: User | None = None
    access: str | None = None
    refresh: str | None = None


def issue_tokens(user: User, family: uuid.UUID | None = None) -> tuple[str, str]:
    """Create an access/refresh pair and record the refresh as active."""
    access = AccessToken.for_user(user)
    refresh = RefreshToken.for_user(user)
    RefreshTokenRecord.objects.create(
        user=user,
        jti=str(refresh["jti"]),
        family=family or uuid.uuid4(),
    )
    return str(access), str(refresh)


def read_refresh(raw: str | None) -> tuple[int, str] | None:
    """Verify signature + expiry of a refresh token; return (user_id, jti)."""
    if not raw:
        return None
    try:
        payload = RefreshToken(raw)  # raises TokenError when invalid/expired
        return int(payload[api_settings.USER_ID_CLAIM]), str(payload["jti"])
    except (TokenError, KeyError, TypeError, ValueError, IndexError):
        return None


def verified_user_id(raw: str | None) -> int | None:
    """User id from a *verified* refresh token (used to key the rate limit)."""
    parsed = read_refresh(raw)
    return parsed[0] if parsed else None


def _revoke_family(family: uuid.UUID) -> int:
    now = timezone.now()
    return RefreshTokenRecord.objects.filter(
        family=family,
        revoked_at__isnull=True,
    ).update(revoked_at=now)


def rotate_refresh(raw: str | None, request_id: str = "-") -> RotationResult:
    """Validate the presented refresh token and rotate it exactly once."""
    parsed = read_refresh(raw)
    if parsed is None:
        return RotationResult(INVALID if raw else MISSING)

    user_id, jti = parsed
    with transaction.atomic():
        record = (
            RefreshTokenRecord.objects.select_related("user")
            .filter(jti=jti)
            .first()
        )
        if record is None:
            # Signed by us but unknown (pruned or forged with the key): refuse.
            return RotationResult(INVALID)

        if record.is_revoked:
            revoked = _revoke_family(record.family)
            logger.warning(
                "refresh_token_replay_blocked",
                extra={
                    "request_id": request_id,
                    "family": str(record.family),
                    "revoked_count": revoked,
                },
            )
            return RotationResult(REPLAYED)

        user = record.user
        if not user.is_active:
            record.revoked_at = timezone.now()
            record.save(update_fields=["revoked_at"])
            return RotationResult(INACTIVE)

        new_access, new_refresh = issue_tokens(user, family=record.family)
        record.revoked_at = timezone.now()
        record.replaced_by_jti = str(RefreshToken(new_refresh)["jti"])
        record.save(update_fields=["revoked_at", "replaced_by_jti"])

    return RotationResult(ROTATED, user=user, access=new_access, refresh=new_refresh)


def revoke_family_for(raw: str | None) -> bool:
    """Logout: revoke every active token in the presented family (idempotent)."""
    parsed = read_refresh(raw)
    if parsed is None:
        return False
    _, jti = parsed
    record = RefreshTokenRecord.objects.filter(jti=jti).first()
    if record is None:
        return False
    _revoke_family(record.family)
    return True


def set_refresh_cookie(response: HttpResponse, token: str) -> None:
    """HttpOnly refresh cookie scoped to the auth endpoints (docs/05 section 3)."""
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=REFRESH_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
    )


def delete_refresh_cookie(response: HttpResponse) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite=REFRESH_COOKIE_SAMESITE,
    )
