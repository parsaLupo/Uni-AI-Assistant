"""Shared fixtures for the Phase 03 auth tests.

DRF throttles share the default cache across tests, so every test starts with a
clean bucket (rates are 10/min — a shared bucket would fail unrelated tests).
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import Role, User

TEST_PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def login(client: APIClient, email: str, password: str = TEST_PASSWORD):
    """POST /api/v1/auth/login/ with a JSON body (as the SPA does).

    On success the Bearer token is installed on the client, exactly what the
    browser's in-memory token does for subsequent API calls (docs/05 section 3).
    """
    response = client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )
    if response.status_code == 200:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    return response


def make_user(email: str, role: Role = Role.STUDENT, **extra) -> User:
    user = User.objects.create_user(
        email=email,
        password=TEST_PASSWORD,
        role=role,
        **extra,
    )
    return user


@pytest.fixture
def student() -> User:
    return make_user("student@example.edu", Role.STUDENT, first_name="سارا")


@pytest.fixture
def professor() -> User:
    return make_user("professor@example.edu", Role.PROFESSOR)


@pytest.fixture
def admin() -> User:
    return make_user("admin@example.edu", Role.ADMIN)


@pytest.fixture
def superadmin() -> User:
    return make_user("root@example.edu", Role.SUPERADMIN)


def csrf_header(client: APIClient) -> dict[str, str]:
    """Echo the csrftoken cookie Django set at login (double submit, OA-23).

    Sent as a WSGI environ key (HTTP_X_CSRFTOKEN) — the guaranteed mechanism
    for the Django/DRF test client, which `request.headers` maps back to
    `X-CSRFToken`.
    """
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


def is_persian(value) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in str(value))
