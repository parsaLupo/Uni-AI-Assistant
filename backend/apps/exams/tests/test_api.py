"""Exam endpoints: one-per-offering admin surface + public list + history."""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.courses.models import CourseOffering
from apps.exams.models import Exam

pytestmark = pytest.mark.django_db


@pytest.fixture
def offering_row(academic_graph):
    return CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )


@pytest.fixture
def past_offering_row(academic_graph):
    return CourseOffering.objects.create(
        course=academic_graph["prereq"], term=academic_graph["past_term"], section_code="01"
    )


def _payload():
    starts = timezone.now() + timezone.timedelta(days=20)
    return {
        "starts_at": starts.isoformat(),
        "ends_at": (starts + timezone.timedelta(hours=2)).isoformat(),
        "classroom": "تالار امتحان ۱",
    }


def test_admin_sets_exam_for_offering_then_updates(authed_client, admin, offering_row):
    client = authed_client(admin)
    url = f"/api/v1/admin/offerings/{offering_row.pk}/exam/"
    created = client.put(url, _payload(), format="json")  # catalog: GET/PUT/PATCH
    assert created.status_code == 201
    exam_id = created.json()["id"]

    # POST is not part of the contract → documented 405 envelope.
    post = client.post(url, _payload(), format="json")
    assert post.status_code == 405
    assert post.json()["error"]["code"] == "METHOD_NOT_ALLOWED"

    fetched = client.get(url)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == exam_id

    patched = client.patch(url, {"classroom": "سالن ۲"}, format="json")
    assert patched.status_code == 200
    exam = Exam.objects.get(pk=exam_id)
    assert exam.classroom == "سالن ۲"


def test_anonymous_cannot_set_exams(api_client, offering_row):
    assert api_client.get(f"/api/v1/admin/offerings/{offering_row.pk}/exam/").status_code == 401


def test_historical_exam_is_frozen(authed_client, admin, past_offering_row):
    client = authed_client(admin)
    url = f"/api/v1/admin/offerings/{past_offering_row.pk}/exam/"
    response = client.put(url, _payload(), format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_public_exam_list_filters_by_term(authed_client, student, offering_row, academic_graph):
    Exam.objects.create(
        course_offering=offering_row,
        starts_at=timezone.now() + timezone.timedelta(days=20),
        ends_at=timezone.now() + timezone.timedelta(days=20, hours=2),
    )
    client = authed_client(student)
    all_exams = client.get("/api/v1/exams/").json()["results"]
    assert len(all_exams) == 1
    current = client.get("/api/v1/exams/", {"term": "current"}).json()["results"]
    assert len(current) == 1
    other = client.get("/api/v1/exams/", {"term": "999"}).json()["results"]
    assert other == []
    assert all_exams[0]["course_offering"]["course_code"] == academic_graph["course"].code


def test_exam_payload_carries_term_context(authed_client, student, offering_row, academic_graph):
    """Phase 06: every exam row shows its term, so the payload must nest it."""
    Exam.objects.create(
        course_offering=offering_row,
        starts_at=timezone.now() + timezone.timedelta(days=20),
        ends_at=timezone.now() + timezone.timedelta(days=20, hours=2),
    )
    body = authed_client(student).get("/api/v1/exams/").json()["results"][0]
    term = body["course_offering"]["term"]
    assert term["id"] == academic_graph["term"].pk
    assert term["name"] == academic_graph["term"].name


def test_student_me_filter_only_returns_own_enrolled_exams(
    authed_client, admin, student_profile, offering_row
):
    """The documented `?student=me` filter joins `enrollments`, not `enrollment`."""
    from apps.students.models import Enrollment

    exam = Exam.objects.create(
        course_offering=offering_row,
        starts_at=timezone.now() + timezone.timedelta(days=20),
        ends_at=timezone.now() + timezone.timedelta(days=20, hours=2),
    )
    client = authed_client(student_profile.user)

    # Not enrolled yet: the exam is visible in the full list, absent from "mine".
    assert len(client.get("/api/v1/exams/").json()["results"]) == 1
    assert client.get("/api/v1/exams/", {"student": "me"}).json()["results"] == []

    Enrollment.objects.create(student=student_profile, course_offering=offering_row)
    mine = client.get("/api/v1/exams/", {"student": "me"}).json()["results"]
    assert [row["id"] for row in mine] == [exam.pk]

    # A staff account has no student profile: documented filter yields 200 + [],
    # never an AttributeError-driven 500.
    staff = authed_client(admin).get("/api/v1/exams/", {"student": "me"})
    assert staff.status_code == 200
    assert staff.json()["results"] == []
def test_student_does_not_see_exams_from_other_programs(
    authed_client, student_profile, academic_graph
):
    from apps.academics.models import Department
    from apps.courses.models import Course, CourseOffering
    from apps.exams.models import Exam
    from django.utils import timezone

    other_dept = Department.objects.create(
        faculty=academic_graph["faculty"], name="گروه ریاضی", code="99"
    )
    other_course = Course.objects.create(
        department=other_dept, code="MATH101", title="ریاضی", credits=3
    )
    other_offering = CourseOffering.objects.create(
        course=other_course, term=academic_graph["term"], section_code="01"
    )
    other_exam = Exam.objects.create(
        course_offering=other_offering,
        starts_at=timezone.now() + timezone.timedelta(days=20),
        ends_at=timezone.now() + timezone.timedelta(days=20, hours=2),
    )

    own_offering = CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="02"
    )
    own_exam = Exam.objects.create(
        course_offering=own_offering,
        starts_at=timezone.now() + timezone.timedelta(days=21),
        ends_at=timezone.now() + timezone.timedelta(days=21, hours=2),
    )

    client = authed_client(student_profile.user)
    ids = [row["id"] for row in client.get("/api/v1/exams/").json()["results"]]
    assert own_exam.pk in ids
    assert other_exam.pk not in ids

