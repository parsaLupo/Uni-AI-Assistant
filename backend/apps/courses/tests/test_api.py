"""Course catalog API: reads, search (C-05), filters, prerequisites, history."""

from __future__ import annotations

from datetime import time

import pytest
from django.utils import timezone

from apps.courses.models import ClassSchedule, Course, CourseOffering, CoursePrerequisite, Weekday
from apps.exams.models import Exam
from apps.professors.models import Professor

pytestmark = pytest.mark.django_db


@pytest.fixture
def offerings(academic_graph):
    prof = Professor.objects.create(
        department=academic_graph["department"],
        first_name="مریم",
        last_name="رضایی",
        academic_title="استادیار",
    )
    current = CourseOffering.objects.create(
        course=academic_graph["course"],
        term=academic_graph["term"],
        professor=prof,
        section_code="01",
        capacity=30,
    )
    past = CourseOffering.objects.create(
        course=academic_graph["course"],
        term=academic_graph["past_term"],
        section_code="01",
        capacity=25,
    )
    ClassSchedule.objects.create(
        course_offering=current,
        weekday=Weekday.SATURDAY,
        start_time=time(10, 0),
        end_time=time(12, 0),
        classroom="کلاس ۱۰۱",
    )
    Exam.objects.create(
        course_offering=current,
        starts_at=timezone.now() + timezone.timedelta(days=30),
        ends_at=timezone.now() + timezone.timedelta(days=30, hours=2),
    )
    return {"current": current, "past": past, "professor": prof}


def test_anonymous_cannot_read_catalog(api_client):
    assert api_client.get("/api/v1/courses/").status_code == 401
    assert api_client.get("/api/v1/course-offerings/").status_code == 401


def test_student_reads_courses_with_prerequisites(authed_client, student, academic_graph):
    CoursePrerequisite.objects.create(
        course=academic_graph["course"], prerequisite_course=academic_graph["prereq"]
    )
    client = authed_client(student)
    response = client.get("/api/v1/courses/")
    assert response.status_code == 200
    course = next(c for c in response.json()["results"] if c["code"] == "1916001")
    assert course["prerequisites"][0]["code"] == "1916002"
    assert course["department"]["name"] == "گروه مهندسی کامپیوتر"


def test_prerequisite_relation_works_in_both_directions(academic_graph):
    edge = CoursePrerequisite.objects.create(
        course=academic_graph["course"], prerequisite_course=academic_graph["prereq"]
    )
    assert list(academic_graph["course"].prerequisite_edges.values_list(
        "prerequisite_course__code", flat=True
    )) == ["1916002"]
    assert list(
        academic_graph["prereq"].dependent_edges.values_list("course__code", flat=True)
    ) == ["1916001"]
    assert edge.course != edge.prerequisite_course


def test_search_survives_arabic_variant_input(authed_client, student, academic_graph):
    Course.objects.create(
        department=academic_graph["department"],
        code="1916999",
        title="علوم کامپیوتر",
        credits=3,
    )
    client = authed_client(student)
    # Same words typed with Arabic kaf/yeh and no space — must still match.
    response = client.get("/api/v1/courses/", {"search": "علومكامپيوتر"})
    assert response.status_code == 200
    codes = [c["code"] for c in response.json()["results"]]
    assert "1916999" in codes


def test_offering_filters_term_current_and_course(
    authed_client, student, offerings, academic_graph
):
    client = authed_client(student)
    response = client.get("/api/v1/course-offerings/", {"term": "current"})
    results = response.json()["results"]
    assert [o["id"] for o in results] == [offerings["current"].pk]

    by_course = client.get(
        "/api/v1/course-offerings/", {"course": academic_graph["course"].code}
    ).json()["results"]
    assert len(by_course) == 2  # current + past section


def test_offering_detail_embeds_schedules_and_exam(authed_client, student, offerings):
    response = authed_client(student).get(
        f"/api/v1/course-offerings/{offerings['current'].pk}/"
    )
    body = response.json()
    assert body["schedules"][0]["classroom"] == "کلاس ۱۰۱"
    assert body["exam"]["starts_at"]
    assert body["professor"]["last_name"] == "رضایی"
    assert body["enrolled_count"] == 0


def test_student_cannot_write_courses(authed_client, student, academic_graph):
    client = authed_client(student)
    response = client.post(
        "/api/v1/admin/courses/",
        {"code": "1916000", "title": "x", "credits": 2,
         "department_id": academic_graph["department"].pk},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_create_course_and_duplicate_returns_409(authed_client, admin, academic_graph):
    client = authed_client(admin)
    payload = {
        "code": "1916777",
        "title": "آزمون",
        "credits": 2,
        "department_id": academic_graph["department"].pk,
    }
    assert client.post("/api/v1/admin/courses/", payload, format="json").status_code == 201
    duplicate = client.post("/api/v1/admin/courses/", payload, format="json")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"


def test_admin_prerequisite_nested_endpoints(authed_client, admin, academic_graph):
    client = authed_client(admin)
    course_id = academic_graph["course"].pk
    created = client.post(
        f"/api/v1/admin/courses/{course_id}/prerequisites/",
        {"prerequisite_course_id": academic_graph["prereq"].pk},
        format="json",
    )
    assert created.status_code == 201
    edge_id = created.json()["id"]

    listed = client.get(f"/api/v1/admin/courses/{course_id}/prerequisites/")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    duplicate = client.post(
        f"/api/v1/admin/courses/{course_id}/prerequisites/",
        {"prerequisite_course_id": academic_graph["prereq"].pk},
        format="json",
    )
    assert duplicate.status_code == 409

    self_edge = client.post(
        f"/api/v1/admin/courses/{course_id}/prerequisites/",
        {"prerequisite_course_id": course_id},
        format="json",
    )
    assert self_edge.status_code == 409

    assert client.delete(f"/api/v1/admin/prerequisites/{edge_id}/").status_code == 204


def test_historical_offering_is_immutable(authed_client, admin, offerings):
    client = authed_client(admin)
    past = offerings["past"]
    update = client.patch(
        f"/api/v1/admin/offerings/{past.pk}/", {"capacity": 99}, format="json"
    )
    assert update.status_code == 409
    assert update.json()["error"]["code"] == "CONFLICT"
    delete = client.delete(f"/api/v1/admin/offerings/{past.pk}/")
    assert delete.status_code == 409
    past.refresh_from_db()
    assert past.capacity == 25


def test_current_offering_is_editable_and_audited(authed_client, admin, offerings):
    from apps.analytics.models import AuditLog

    client = authed_client(admin)
    current = offerings["current"]
    update = client.patch(
        f"/api/v1/admin/offerings/{current.pk}/", {"capacity": 40}, format="json"
    )
    assert update.status_code == 200
    current.refresh_from_db()
    assert current.capacity == 40
    assert AuditLog.objects.filter(
        entity_type="courses.CourseOffering", action="UPDATE"
    ).exists()


def test_list_endpoint_emits_metrics_log(authed_client, student, caplog):
    import logging

    with caplog.at_level(logging.INFO, logger="app.metrics"):
        response = authed_client(student).get("/api/v1/courses/")
    assert response.status_code == 200
    assert any(r.message == "list_endpoint" for r in caplog.records)


def test_missing_object_detail_returns_404_envelope_not_500(authed_client, admin):
    """Regression: a view-level Http404 used to crash the shared error handler.

    DRF's default exception_handler converts Django's Http404 into its NotFound
    only while building the Response, so `_translate` received the original
    object without `.detail` and raised AttributeError — the client saw a 500.
    Caught by live testing (DELETE /api/v1/admin/courses/9999999/ against the
    compose stack); no unit test covered view-level 404s before this.
    """
    response = authed_client(admin).delete("/api/v1/admin/courses/9999999/")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["message"]  # Persian message, never a stack trace
    # DRF's internal English detail ("No Course matches...") must not leak:
    # only Persian text may reach the client as `message` (ADR-010).
    assert any("\u0600" <= ch <= "\u06ff" for ch in error["message"])

