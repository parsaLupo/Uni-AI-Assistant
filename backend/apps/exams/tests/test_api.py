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
