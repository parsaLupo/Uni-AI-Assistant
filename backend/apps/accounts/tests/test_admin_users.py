"""Admin user management: the permission matrix (docs/api/admin.md, ADR-014)."""

from __future__ import annotations

import pytest

from apps.accounts.models import Role, User

from .conftest import TEST_PASSWORD, is_persian, login

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/users/"


def create(client, email: str, role: str = Role.STUDENT, password: str = TEST_PASSWORD):
    return client.post(
        URL,
        {"email": email, "password": password, "role": role},
        format="json",
    )


# Authentication and authorization gates (phase criteria) --------------------


def test_anonymous_is_rejected(api_client):
    response = api_client.get(URL)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_student_is_rejected_with_permission_denied(api_client, student):
    login(api_client, student.email)

    response = api_client.get(URL)

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "PERMISSION_DENIED"
    assert is_persian(error["message"])


def test_admin_endpoint_is_not_reachable_with_a_students_token_alone(
    api_client, student, professor
):
    """A valid token for the wrong role is still a 403, not a 200."""
    login(api_client, professor.email)  # PROFESSOR is not privileged
    response = api_client.get(URL)
    assert response.status_code == 403


# Listing and filtering ------------------------------------------------------


def test_admin_can_list_users(api_client, admin, student):
    login(api_client, admin.email)

    response = api_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    # Pagination contract (docs/04 section 4).
    assert "count" in body and "results" in body
    emails = {row["email"] for row in body["results"]}
    assert {admin.email, student.email} <= emails


def test_admin_can_filter_by_role(api_client, admin, student, professor):
    login(api_client, admin.email)

    response = api_client.get(f"{URL}?role=STUDENT")

    assert response.status_code == 200
    assert {row["email"] for row in response.json()["results"]} == {student.email}


# Creating accounts (ADR-014 decision 2) -------------------------------------


def test_admin_can_create_a_professor_account(api_client, admin):
    login(api_client, admin.email)

    response = create(api_client, "new-professor@example.edu", role=Role.PROFESSOR)

    assert response.status_code == 201
    assert response.json()["role"] == Role.PROFESSOR
    # The password must never come back in a response body.
    assert "password" not in response.json()
    assert User.objects.get(email="new-professor@example.edu").role == Role.PROFESSOR


def test_admin_cannot_create_a_privileged_account(api_client, admin):
    login(api_client, admin.email)

    response = create(api_client, "sneaky@example.edu", role=Role.ADMIN)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
    assert not User.objects.filter(email="sneaky@example.edu").exists()


def test_superadmin_can_create_an_admin(api_client, superadmin):
    login(api_client, superadmin.email)

    response = create(api_client, "new-admin@example.edu", role=Role.ADMIN)

    assert response.status_code == 201
    assert response.json()["role"] == Role.ADMIN


def test_duplicate_email_returns_conflict(api_client, admin, student):
    login(api_client, admin.email)

    response = create(api_client, student.email)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


# Role changes and deactivation ----------------------------------------------


def test_admin_can_promote_to_professor_but_not_to_admin(api_client, admin, student):
    login(api_client, admin.email)

    promoted = api_client.patch(
        f"{URL}{student.id}/",
        {"role": Role.PROFESSOR},
        format="json",
    )
    elevated = api_client.patch(
        f"{URL}{student.id}/",
        {"role": Role.ADMIN},
        format="json",
    )

    assert promoted.status_code == 200
    assert promoted.json()["role"] == Role.PROFESSOR
    assert elevated.status_code == 403
    assert elevated.json()["error"]["code"] == "PERMISSION_DENIED"


def test_superadmin_can_assign_the_admin_role(api_client, superadmin, student):
    login(api_client, superadmin.email)

    response = api_client.patch(
        f"{URL}{student.id}/",
        {"role": Role.ADMIN},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["role"] == Role.ADMIN


def test_delete_deactivates_instead_of_removing(api_client, admin, student):
    login(api_client, admin.email)

    response = api_client.delete(f"{URL}{student.id}/")

    assert response.status_code == 204
    student.refresh_from_db()
    assert student.is_active is False
    assert User.objects.filter(email=student.email).exists()


def test_admin_cannot_deactivate_themselves(api_client, admin):
    login(api_client, admin.email)

    response = api_client.delete(f"{URL}{admin.id}/")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert is_persian(response.json()["error"]["message"])
    admin.refresh_from_db()
    assert admin.is_active is True


def test_admin_cannot_deactivate_a_superadmin(api_client, admin, superadmin):
    login(api_client, admin.email)

    response = api_client.delete(f"{URL}{superadmin.id}/")

    assert response.status_code == 403
    superadmin.refresh_from_db()
    assert superadmin.is_active is True
