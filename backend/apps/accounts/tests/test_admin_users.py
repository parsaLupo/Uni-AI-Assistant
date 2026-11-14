"""Admin user management: the permission matrix (docs/api/admin.md, ADR-014)."""

from __future__ import annotations

import pytest

from apps.accounts.models import Role, User
from apps.courses.models import CourseOffering
from apps.students.models import Enrollment, EnrollmentStatus, StudentProfile

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


# Creating student accounts with academic data (profile-improvement Parts 3–4)


@pytest.fixture
def student_graph(academic_graph):
    """Courses + offerings for the conditional student-creation section."""
    from apps.academics.models import Department, Faculty
    from apps.courses.models import Course, CourseOffering

    past_offering = CourseOffering.objects.create(
        course=academic_graph["prereq"],
        term=academic_graph["past_term"],
        section_code="01",
    )
    other_course = Course.objects.create(
        department=academic_graph["department"], code="1916003", title="درس سوم", credits=2
    )
    current_offering = CourseOffering.objects.create(
        course=other_course, term=academic_graph["term"], section_code="01"
    )
    # A course of a *different* department (must be rejected as a pass).
    other_faculty = Faculty.objects.create(name="دانشکده دیگر", code="F-OTHER")
    other_department = Department.objects.create(
        faculty=other_faculty, name="گروه دیگر", code="16"
    )
    foreign_course = Course.objects.create(
        department=other_department, code="2531001", title="درس گروه دیگر", credits=2
    )
    foreign_offering = CourseOffering.objects.create(
        course=foreign_course, term=academic_graph["term"], section_code="01"
    )
    return {
        **academic_graph,
        "past_offering": past_offering,
        "other_course": other_course,
        "current_offering": current_offering,
        "foreign_course": foreign_course,
        "foreign_offering": foreign_offering,
    }


def student_payload(graph, email="new-student@example.edu", **overrides):
    from apps.students.models import DegreeLevel

    payload = {
        "email": email,
        "password": TEST_PASSWORD,
        "first_name": "دانشجو",
        "last_name": "جدید",
        "role": Role.STUDENT,
        "student_number": "40412345",
        "department_id": graph["department"].pk,
        "degree_level": DegreeLevel.BACHELOR,
        "entry_year": "1402",
        "passed_course_codes": [graph["prereq"].code, graph["course"].code],
        "current_offering_ids": [graph["current_offering"].pk],
    }
    payload.update(overrides)
    return payload


def test_admin_creates_student_with_profile_and_enrollments(api_client, admin, student_graph):
    login(api_client, admin.email)

    response = api_client.post(URL, student_payload(student_graph), format="json")

    assert response.status_code == 201, response.content
    user = User.objects.get(email="new-student@example.edu")
    assert user.role == Role.STUDENT
    profile = StudentProfile.objects.get(user=user)
    assert profile.student_number == "40412345"
    assert profile.department_id == student_graph["department"].pk
    # Faculty is derived from the major.
    assert profile.faculty_id == student_graph["faculty"].pk
    assert profile.degree_level == "BACHELOR"
    assert profile.entry_year == "1402"

    passed = Enrollment.objects.filter(student=profile, status=EnrollmentStatus.PASSED)
    assert passed.count() == 2
    assert {e.course_offering.course.code for e in passed} == {
        student_graph["prereq"].code,
        student_graph["course"].code,
    }
    # Historical passes live in a past term; grades are never invented.
    assert all(e.course_offering.term.is_current is False for e in passed)
    assert all(e.grade is None for e in passed)

    current = Enrollment.objects.filter(student=profile, status=EnrollmentStatus.ENROLLED)
    assert current.count() == 1
    assert current.get().course_offering_id == student_graph["current_offering"].pk
    assert current.get().course_offering.term.is_current is True
    # No PASSED and ENROLLED row for the same course.
    passed_codes = {e.course_offering.course_id for e in passed}
    assert not passed_codes & {e.course_offering.course_id for e in current}


def test_missing_student_fields_are_rejected_with_persian_errors(api_client, admin, student_graph):
    login(api_client, admin.email)

    payload = student_payload(student_graph)
    for field in ("student_number", "department_id", "degree_level", "entry_year"):
        broken = {key: value for key, value in payload.items() if key != field}
        response = api_client.post(URL, broken, format="json")
        assert response.status_code == 400, field
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert is_persian(error["message"])
    assert not User.objects.filter(email="new-student@example.edu").exists()


def test_student_fields_are_rejected_for_other_roles(api_client, admin, student_graph):
    login(api_client, admin.email)

    response = api_client.post(
        URL,
        student_payload(student_graph, role=Role.PROFESSOR),
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="new-student@example.edu").exists()
    assert not StudentProfile.objects.filter(student_number="40412345").exists()


def test_duplicate_student_number_returns_conflict(api_client, admin, student_graph, academic_graph):
    other_user = User.objects.create_user(email="taken@example.edu", password="x")
    StudentProfile.objects.create(user=other_user, student_number="40412345")
    login(api_client, admin.email)

    response = api_client.post(URL, student_payload(student_graph), format="json")

    assert response.status_code == 409
    assert is_persian(response.json()["error"]["message"])


def test_invalid_entry_year_is_rejected(api_client, admin, student_graph):
    login(api_client, admin.email)

    for year in ("139", "abcd", "9999"):
        response = api_client.post(
            URL, student_payload(student_graph, entry_year=year), format="json"
        )
        assert response.status_code == 400, year
    assert not User.objects.filter(email="new-student@example.edu").exists()


def test_passed_course_outside_the_department_is_rejected(api_client, admin, student_graph):
    login(api_client, admin.email)

    response = api_client.post(
        URL,
        student_payload(
            student_graph,
            passed_course_codes=[student_graph["foreign_course"].code],
        ),
        format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="new-student@example.edu").exists()


def test_current_offering_rules_are_enforced(api_client, admin, student_graph):
    login(api_client, admin.email)
    graph = student_graph
    past_term_offering = CourseOffering.objects.create(
        course=graph["other_course"], term=graph["past_term"], section_code="02"
    )

    # A past-term offering can never be a current take.
    response = api_client.post(
        URL,
        student_payload(student_graph, current_offering_ids=[past_term_offering.pk]),
        format="json",
    )
    assert response.status_code == 400

    # Another department's offering is rejected.
    response = api_client.post(
        URL,
        student_payload(
            student_graph,
            passed_course_codes=[],
            current_offering_ids=[graph["foreign_offering"].pk],
        ),
        format="json",
    )
    assert response.status_code == 400

    # The same course cannot be passed and currently taken.
    response = api_client.post(
        URL,
        student_payload(
            student_graph,
            passed_course_codes=[graph["other_course"].code],
            current_offering_ids=[graph["current_offering"].pk],
        ),
        format="json",
    )
    assert response.status_code == 400

    # Unknown offering id.
    response = api_client.post(
        URL, student_payload(student_graph, current_offering_ids=[987654]), format="json"
    )
    assert response.status_code == 400

    assert not User.objects.filter(email="new-student@example.edu").exists()
    assert Enrollment.objects.count() == 0


def test_failed_creation_rolls_back_all_records(api_client, admin, student_graph, monkeypatch):
    """An error after the user insert leaves zero partial records (atomicity)."""
    from apps.accounts import serializers as accounts_serializers

    login(api_client, admin.email)

    def explode(*args, **kwargs):
        raise RuntimeError("simulated failure after the user insert")

    monkeypatch.setattr(
        accounts_serializers.StudentProfile.objects, "create", explode
    )
    response = api_client.post(URL, student_payload(student_graph), format="json")
    assert response.status_code == 500

    assert not User.objects.filter(email="new-student@example.edu").exists()
    assert not StudentProfile.objects.filter(student_number="40412345").exists()
    assert Enrollment.objects.count() == 0
    assert not CourseOffering.objects.filter(
        course=student_graph["course"], term=student_graph["past_term"], section_code="01"
    ).exists()


def test_professor_creation_stays_unchanged(api_client, admin, student_graph):
    login(api_client, admin.email)

    response = create(api_client, "plain-prof@example.edu", role=Role.PROFESSOR)

    assert response.status_code == 201
    user = User.objects.get(email="plain-prof@example.edu")
    assert user.role == Role.PROFESSOR
    assert not StudentProfile.objects.filter(user=user).exists()
