"""Calendar endpoints: published-only public feed + admin CRUD."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.calendar.models import AcademicEvent, EventType

pytestmark = pytest.mark.django_db


def test_public_feed_shows_only_published_events(authed_client, student, academic_graph):
    AcademicEvent.objects.create(
        term=academic_graph["term"], title="عمومی",
        starts_at=timezone.now(), ends_at=timezone.now() + timedelta(days=1),
        is_published=True,
    )
    AcademicEvent.objects.create(
        term=academic_graph["term"], title="پیش‌نویس",
        starts_at=timezone.now(), ends_at=timezone.now() + timedelta(days=1),
        is_published=False,
    )
    titles = [
        e["title"]
        for e in authed_client(student).get("/api/v1/calendar/events/").json()["results"]
    ]
    assert titles == ["عمومی"]


def test_public_feed_requires_authentication(api_client):
    assert api_client.get("/api/v1/calendar/events/").status_code == 401


def test_admin_creates_event_and_validates_time_range(
    authed_client, admin, academic_graph
):
    client = authed_client(admin)
    payload = {
        "term_id": academic_graph["term"].pk,
        "title": "هفته امتحانات",
        "event_type": EventType.EXAM_WEEK,
        "starts_at": (timezone.now() + timedelta(days=10)).isoformat(),
        "ends_at": (timezone.now() + timedelta(days=10, hours=3)).isoformat(),
        "is_published": True,
    }
    created = client.post("/api/v1/admin/calendar/events/", payload, format="json")
    assert created.status_code == 201
    event_id = created.json()["id"]

    invalid = {**payload, "starts_at": payload["ends_at"], "ends_at": payload["starts_at"]}
    bad = client.post("/api/v1/admin/calendar/events/", invalid, format="json")
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"

    assert client.delete(
        f"/api/v1/admin/calendar/events/{event_id}/"
    ).status_code == 204


def test_student_cannot_create_events(authed_client, student, academic_graph):
    response = authed_client(student).post(
        "/api/v1/admin/calendar/events/",
        {"term_id": academic_graph["term"].pk, "title": "x",
         "starts_at": timezone.now().isoformat(),
         "ends_at": (timezone.now() + timedelta(hours=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 403
