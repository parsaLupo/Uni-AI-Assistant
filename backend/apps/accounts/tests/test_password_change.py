"""POST /auth/password-change/ — the only self-service credential change.

Every signed-in role may change their own password after re-entering the
current one; the presented refresh family is revoked so a stolen refresh
token cannot outlive the credential (profile-improvement Part 1).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import authenticate

from apps.accounts.models import User

from .conftest import TEST_PASSWORD, is_persian, login, make_user

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "Br4nd-New-Pass!"

URL = "/api/v1/auth/password-change/"


def test_student_changes_own_password(api_client, student):
    login(api_client, "student@example.edu")
    response = api_client.post(
        URL,
        {"old_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert is_persian(response.json()["detail"])
    user = User.objects.get(email="student@example.edu")
    assert user.check_password(NEW_PASSWORD)
    assert authenticate(email=user.email, password=NEW_PASSWORD) == user
    # The old credential no longer authenticates.
    assert authenticate(email=user.email, password=TEST_PASSWORD) is None


def test_wrong_current_password_is_rejected(api_client, student):
    login(api_client, "student@example.edu")
    response = api_client.post(
        URL,
        {"old_password": "totally-wrong", "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 400
    body = response.json()
    assert is_persian(body["error"]["message"])
    # The password was not changed.
    assert User.objects.get(email="student@example.edu").check_password(TEST_PASSWORD)


def test_weak_new_password_is_rejected(api_client, student):
    login(api_client, "student@example.edu")
    response = api_client.post(
        URL,
        {"old_password": TEST_PASSWORD, "new_password": "123"},
        format="json",
    )
    assert response.status_code == 400
    assert User.objects.get(email="student@example.edu").check_password(TEST_PASSWORD)


def test_password_change_requires_authentication(api_client):
    response = api_client.post(
        URL,
        {"old_password": "x", "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 401


def test_professor_can_change_own_password(api_client):
    make_user("lect@example.edu", "PROFESSOR")
    login(api_client, "lect@example.edu")
    response = api_client.post(
        URL,
        {"old_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert User.objects.get(email="lect@example.edu").check_password(NEW_PASSWORD)


def test_change_revokes_the_presented_refresh_family(api_client, student):
    """A stolen refresh cookie cannot outlive the credential change."""
    login(api_client, "student@example.edu")
    assert student.refresh_tokens.filter(revoked_at__isnull=True).exists()
    response = api_client.post(
        URL,
        {"old_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert not student.refresh_tokens.filter(revoked_at__isnull=True).exists()
