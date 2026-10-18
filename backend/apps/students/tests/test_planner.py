"""Onboarding (`/students/me/`) and the student planner (`/students/planner/`)."""

from __future__ import annotations

import pytest

from apps.accounts.models import User
from apps.courses.models import CourseOffering, OfferingStatus
from apps.students.models import Enrollment, EnrollmentStatus, StudentProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def offering(academic_graph):
    return CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )


@pytest.fixture
def past_offering(academic_graph):
    return CourseOffering.objects.create(
        course=academic_graph["prereq"], term=academic_graph["past_term"], section_code="01"
    )


def test_me_get_creates_an_empty_profile_row(authed_client, student):
    client = authed_client(student)
    response = client.get("/api/v1/students/me/")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["first_name"] == "سارا"
    assert body["student_number"] is None
    assert body["onboarding_complete"] is False
    assert StudentProfile.objects.filter(user=student).exists()


def test_onboarding_collects_uni_code_and_major(
    authed_client, student, student_profile, academic_graph
):
    client = authed_client(student)
    response = client.patch(
        "/api/v1/students/me/",
        {"student_number": "40498765", "department_id": academic_graph["department"].pk},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["student_number"] == "40498765"
    # Faculty is derived from the chosen major (onboarding stays short).
    assert body["faculty"]["code"] == academic_graph["faculty"].code
    assert body["onboarding_complete"] is True


def test_duplicate_student_number_returns_conflict(
    authed_client, student, student_profile
):
    other_user = User.objects.create_user(email="other@example.edu", password="x")
    StudentProfile.objects.create(user=other_user, student_number="99988877")
    client = authed_client(student)
    response = client.patch(
        "/api/v1/students/me/", {"student_number": "99988877"}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_professor_cannot_use_student_surfaces(authed_client, professor_user):
    client = authed_client(professor_user)
    response = client.get("/api/v1/students/me/")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_planner_requires_onboarding_first(authed_client, student, academic_graph, offering):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/planner/", {"course_offering_id": offering.pk}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_planner_add_list_swap_remove(
    authed_client, student, student_profile, academic_graph, offering
):
    client = authed_client(student)
    added = client.post(
        "/api/v1/students/planner/", {"course_offering_id": offering.pk}, format="json"
    )
    assert added.status_code == 201
    item_id = added.json()["id"]
    assert added.json()["status"] == EnrollmentStatus.PLANNED
    assert added.json()["total_credits"] == academic_graph["course"].credits

    listed = client.get("/api/v1/students/planner/").json()
    assert [i["id"] for i in listed] == [item_id]

    duplicate = client.post(
        "/api/v1/students/planner/", {"course_offering_id": offering.pk}, format="json"
    )
    assert duplicate.status_code == 409

    other = CourseOffering.objects.create(
        course=academic_graph["prereq"], term=academic_graph["term"], section_code="01"
    )
    swapped = client.patch(
        f"/api/v1/students/planner/{item_id}/",
        {"course_offering_id": other.pk},
        format="json",
    )
    assert swapped.status_code == 200
    assert swapped.json()["course_offering"]["id"] == other.pk

    assert client.delete(f"/api/v1/students/planner/{item_id}/").status_code == 204
    assert client.get("/api/v1/students/planner/").json() == []


def test_planner_rejects_past_term_offering(
    authed_client, student, student_profile, past_offering
):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/planner/", {"course_offering_id": past_offering.pk}, format="json"
    )
    assert response.status_code == 409


def test_planner_rejects_closed_offering(authed_client, student, student_profile, offering):
    offering.status = OfferingStatus.CLOSED
    offering.save(update_fields=["status"])
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/planner/", {"course_offering_id": offering.pk}, format="json"
    )
    assert response.status_code == 409


def test_planner_is_scoped_to_the_calling_student(
    authed_client, student, student_profile, offering
):
    client = authed_client(student)
    added = client.post(
        "/api/v1/students/planner/", {"course_offering_id": offering.pk}, format="json"
    )
    item_id = added.json()["id"]

    other_user = User.objects.create_user(email="peer@example.edu", password="x")
    StudentProfile.objects.create(user=other_user, student_number="40400000")
    peer_client = authed_client(other_user)
    assert peer_client.get("/api/v1/students/planner/").json() == []
    assert peer_client.delete(f"/api/v1/students/planner/{item_id}/").status_code == 404
    assert Enrollment.objects.filter(pk=item_id).exists()

