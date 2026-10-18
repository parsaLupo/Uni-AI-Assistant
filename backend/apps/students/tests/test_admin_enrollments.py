"""Admin enrollment management: grade rules, filters, historical carve-out (D4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.courses.models import CourseOffering
from apps.students.models import Enrollment, EnrollmentStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def rows(student_profile, academic_graph):
    current_offering = CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )
    past_offering = CourseOffering.objects.create(
        course=academic_graph["prereq"], term=academic_graph["past_term"], section_code="01"
    )
    enrolled = Enrollment.objects.create(
        student=student_profile, course_offering=current_offering,
        status=EnrollmentStatus.ENROLLED,
    )
    historical = Enrollment.objects.create(
        student=student_profile, course_offering=past_offering,
        status=EnrollmentStatus.ENROLLED,
    )
    return {"enrolled": enrolled, "historical": historical}


def test_anonymous_and_student_cannot_manage_enrollments(api_client, authed_client, student, rows):
    assert api_client.get("/api/v1/admin/enrollments/").status_code == 401
    assert authed_client(student).get("/api/v1/admin/enrollments/").status_code == 403


def test_admin_sets_grade_with_status_rules(authed_client, admin, rows):
    client = authed_client(admin)
    # Grade on plain ENROLLED is invalid → documented 400.
    bad = client.patch(
        f"/api/v1/admin/enrollments/{rows['enrolled'].pk}/",
        {"grade": "17.50"},
        format="json",
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"

    # PASSED requires a grade — give it together.
    ok = client.patch(
        f"/api/v1/admin/enrollments/{rows['enrolled'].pk}/",
        {"status": "PASSED", "grade": "17.50"},
        format="json",
    )
    assert ok.status_code == 200, ok.json()
    rows["enrolled"].refresh_from_db()
    assert rows["enrolled"].grade == Decimal("17.50")


def test_grade_out_of_range_rejected(authed_client, admin, rows):
    response = authed_client(admin).patch(
        f"/api/v1/admin/enrollments/{rows['enrolled'].pk}/",
        {"status": "FAILED", "grade": "25"},
        format="json",
    )
    assert response.status_code == 400


def test_grade_correction_on_historical_row_is_allowed(
    authed_client, admin, rows
):
    """D4 carve-out: past-term grade corrections stay possible (audited)."""
    from apps.analytics.models import AuditLog

    client = authed_client(admin)
    response = client.patch(
        f"/api/v1/admin/enrollments/{rows['historical'].pk}/",
        {"status": "PASSED", "grade": "12.00"},
        format="json",
    )
    assert response.status_code == 200
    assert AuditLog.objects.filter(
        entity_type="students.Enrollment", action="UPDATE"
    ).exists()


def test_deleting_historical_enrollment_is_blocked(authed_client, admin, rows):
    client = authed_client(admin)
    response = client.delete(f"/api/v1/admin/enrollments/{rows['historical'].pk}/")
    assert response.status_code == 409
    assert Enrollment.objects.filter(pk=rows["historical"].pk).exists()
    # Current-term rows remain deletable.
    assert client.delete(f"/api/v1/admin/enrollments/{rows['enrolled'].pk}/").status_code == 204


def test_admin_enrollment_filters(authed_client, admin, student, rows, academic_graph):
    client = authed_client(admin)
    by_term = client.get(
        "/api/v1/admin/enrollments/", {"term": "current"}
    ).json()["results"]
    assert [r["id"] for r in by_term] == [rows["enrolled"].pk]

    by_student = client.get(
        "/api/v1/admin/enrollments/", {"student": str(student.pk)}
    ).json()["results"]
    assert len(by_student) == 2

    by_status = client.get(
        "/api/v1/admin/enrollments/", {"status": "ENROLLED"}
    ).json()["results"]
    assert len(by_status) == 2


def test_student_profiles_admin_list_search(authed_client, admin, student_profile):
    client = authed_client(admin)
    response = client.get("/api/v1/admin/students/", {"search": "40411234"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["id"] for r in results] == [student_profile.pk]
