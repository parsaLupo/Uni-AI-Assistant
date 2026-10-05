"""Phase 03 required tests: login, refresh, logout, permissions, own-resource.

Plus ADR-014 specifics: role not client-selectable, rotation with replay
detection, CSRF double-submit, Argon2 hashing, email normalization (FR-AUTH-001…005).
"""

from __future__ import annotations

import jwt
import pytest

from apps.accounts.models import RefreshTokenRecord, Role, User
from apps.accounts.tokens import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH

from .conftest import TEST_PASSWORD, csrf_header, is_persian, login, make_user

pytestmark = pytest.mark.django_db

EMAIL = "student@example.edu"


def register(client, **overrides):
    payload = {
        "email": EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "سارا",
        "last_name": "محمدی",
        **overrides,
    }
    return client.post("/api/v1/auth/register/", payload, format="json")


# Registration (FR-AUTH-001, ADR-014 decision 2) -----------------------------


def test_register_creates_student_and_signs_in(api_client):
    response = register(api_client)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "STUDENT"
    assert body["user"]["email"] == EMAIL
    assert body["access"]

    # Both cookies land as documented (docs/api/auth.md).
    refresh = api_client.cookies[REFRESH_COOKIE_NAME]
    assert refresh["path"] == REFRESH_COOKIE_PATH
    assert refresh["httponly"] is True
    assert "csrftoken" in api_client.cookies


def test_register_ignores_a_client_supplied_role(api_client):
    """Privileged roles can only be provisioned by an admin (ADR-014 decision 2)."""
    response = register(api_client, role="SUPERADMIN")

    assert response.status_code == 201
    assert response.json()["user"]["role"] == "STUDENT"
    assert User.objects.get(email=EMAIL).role == Role.STUDENT


def test_register_duplicate_email_returns_conflict(api_client):
    assert register(api_client).status_code == 201

    response = register(api_client)

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CONFLICT"
    assert is_persian(error["message"])


def test_register_rejects_weak_password_with_persian_field_errors(api_client):
    response = register(api_client, password="123")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert is_persian(error["details"])


def test_register_normalizes_email(api_client):
    response = register(api_client, email="Student@Example.EDU")

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "student@example.edu"


# Login (FR-AUTH-002) --------------------------------------------------------


def test_login_success_returns_access_and_sets_cookies(api_client):
    register(api_client)
    api_client.cookies.clear()

    response = login(api_client, EMAIL)

    assert response.status_code == 200
    assert response.json()["user"]["email"] == EMAIL
    assert response.json()["access"]
    assert REFRESH_COOKIE_NAME in api_client.cookies
    assert "csrftoken" in api_client.cookies


def test_login_invalid_password_is_rejected(api_client):
    register(api_client)
    api_client.cookies.clear()

    response = login(api_client, EMAIL, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_login_unknown_email_gives_the_same_message_as_a_wrong_password(api_client):
    """No user-enumeration oracle: identical status and message for both cases."""
    register(api_client)
    api_client.cookies.clear()

    wrong_password = login(api_client, EMAIL, password="wrong-password")
    unknown_email = login(api_client, "nobody@example.edu", password="whatever-123")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert (
        wrong_password.json()["error"]["message"]
        == unknown_email.json()["error"]["message"]
    )


def test_inactive_account_cannot_log_in(api_client):
    register(api_client)
    User.objects.filter(email=EMAIL).update(is_active=False)
    api_client.cookies.clear()

    response = login(api_client, EMAIL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


# Protected resource + own-resource access (phase list) ----------------------


def test_me_requires_a_bearer_token(api_client):
    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_me_returns_own_resource(api_client):
    register(api_client)
    login(api_client, EMAIL)
    me = api_client.get("/api/v1/auth/me/")

    assert me.status_code == 200
    assert me.json()["email"] == EMAIL
    assert me.json()["role"] == "STUDENT"


def test_me_never_returns_another_users_profile(api_client, student, professor):
    """Own-resource access: a token only ever resolves to its own user."""
    login(api_client, professor.email)
    as_professor = api_client.get("/api/v1/auth/me/").json()
    api_client.cookies.clear()

    login(api_client, student.email)
    as_student = api_client.get("/api/v1/auth/me/").json()

    assert as_professor["id"] == professor.id
    assert as_student["id"] == student.id
    assert as_professor["id"] != as_student["id"]


def test_garbage_bearer_token_is_a_401_envelope_not_a_500(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


# Refresh (FR-AUTH-003, ADR-014 decision 3) ----------------------------------


def test_refresh_rotates_the_refresh_token(api_client):
    register(api_client)
    first_refresh = api_client.cookies[REFRESH_COOKIE_NAME].value

    response = api_client.post(
        "/api/v1/auth/refresh/",
        **csrf_header(api_client),
    )

    assert response.status_code == 200
    assert response.json()["access"]
    second_refresh = api_client.cookies[REFRESH_COOKIE_NAME].value
    assert second_refresh != first_refresh
    # The old record is revoked and points at its replacement.
    payload = jwt.decode(first_refresh, options={"verify_signature": False})
    old = RefreshTokenRecord.objects.get(jti=payload["jti"])
    assert old.revoked_at is not None
    assert old.replaced_by_jti


def test_refresh_requires_the_csrf_header(api_client):
    register(api_client)

    response = api_client.post("/api/v1/auth/refresh/")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
    assert is_persian(response.json()["error"]["message"])


def test_refresh_rejects_a_mismatched_csrf_header(api_client):
    register(api_client)

    response = api_client.post(
        "/api/v1/auth/refresh/",
        HTTP_X_CSRFTOKEN="forged-token",
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_replaying_a_rotated_token_revokes_the_whole_family(api_client):
    """Token theft response (ADR-014 decision 3)."""
    register(api_client)
    stolen = api_client.cookies[REFRESH_COOKIE_NAME].value

    # Legitimate rotation happens on another tab/device.
    assert (
        api_client.post(
            "/api/v1/auth/refresh/",
            **csrf_header(api_client),
        ).status_code
        == 200
    )

    # Attacker replays the stolen token.
    api_client.cookies[REFRESH_COOKIE_NAME] = stolen
    replay = api_client.post(
        "/api/v1/auth/refresh/",
        **csrf_header(api_client),
    )

    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    # The family revocation invalidates even the "current" token.
    assert not RefreshTokenRecord.objects.filter(revoked_at__isnull=True).exists()
    api_client.cookies[REFRESH_COOKIE_NAME] = stolen
    follow_up = api_client.post(
        "/api/v1/auth/refresh/",
        **csrf_header(api_client),
    )
    assert follow_up.status_code == 401


def test_refresh_without_a_refresh_cookie_ends_the_session(api_client):
    """Valid CSRF pair, but the refresh cookie is gone → 401, not 403."""
    register(api_client)
    del api_client.cookies[REFRESH_COOKIE_NAME]

    response = api_client.post(
        "/api/v1/auth/refresh/",
        **csrf_header(api_client),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


# Logout (FR-AUTH-004) -------------------------------------------------------


def test_logout_revokes_the_family_and_clears_the_cookie(api_client):
    register(api_client)
    assert api_client.cookies.get(REFRESH_COOKIE_NAME)

    response = api_client.post(
        "/api/v1/auth/logout/",
        **csrf_header(api_client),
    )

    assert response.status_code == 204
    # Django clears a cookie by sending it back empty with epoch expiry; the
    # test client keeps that tombstone entry, so assert on its value, not on
    # the Morsel's presence.
    assert api_client.cookies.get(REFRESH_COOKIE_NAME, {}).value == ""
    # Every token in the family is revoked, so a stolen cookie is dead too.
    assert not RefreshTokenRecord.objects.filter(revoked_at__isnull=True).exists()
    follow_up = api_client.post(
        "/api/v1/auth/refresh/",
        **csrf_header(api_client),
    )
    assert follow_up.status_code == 401


def test_logout_is_idempotent_without_a_refresh_cookie(api_client):
    register(api_client)
    del api_client.cookies[REFRESH_COOKIE_NAME]

    response = api_client.post(
        "/api/v1/auth/logout/",
        **csrf_header(api_client),
    )

    assert response.status_code == 204


# Identity and hashing (docs/07 section 2, ADR-014 decision 6) ---------------


def test_password_is_hashed_with_argon2id(student):
    assert "$argon2id$" in student.password
    assert student.check_password(TEST_PASSWORD)
    assert not student.check_password("not-the-password")


def test_email_is_stored_normalized():
    user = make_user("Mixed.Case@Example.EDU")

    assert user.email == "mixed.case@example.edu"

