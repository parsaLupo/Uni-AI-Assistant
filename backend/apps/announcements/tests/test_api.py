"""Public announcement feed: expiry, publication and audience scoping (C-03)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.announcements.models import Announcement, AnnouncementPriority

pytestmark = pytest.mark.django_db


def _announce(**kwargs) -> Announcement:
    defaults = {
        "title": "اطلاعیه آزمایشی",
        "body": "متن اطلاعیه",
        "is_published": True,
        "published_at": timezone.now(),
    }
    defaults.update(kwargs)
    return Announcement.objects.create(**defaults)


def test_feed_hides_unpublished_and_expired(authed_client, student, academic_graph):
    client = authed_client(student)
    _announce(title="فعال")
    _announce(title="منقضی", expires_at=timezone.now() - timedelta(hours=1))
    _announce(title="پیش‌نویس", is_published=False)

    titles = [a["title"] for a in client.get("/api/v1/announcements/").json()["results"]]
    assert titles == ["فعال"]


def test_feed_scopes_by_audience_department(
    authed_client, student, student_profile, academic_graph
):
    from apps.academics.models import Department, Faculty

    other_faculty = Faculty.objects.create(name="دانشکده دیگر", code="F-OTHER")
    other_dept = Department.objects.create(
        faculty=other_faculty, name="گروه دیگر", code="77"
    )
    _announce(title="همگانی")
    _announce(title="گروه من", audience_department=academic_graph["department"])
    _announce(title="گروه دیگر", audience_department=other_dept)
    _announce(title="دانشکده دیگر", audience_faculty=other_faculty)

    titles = [
        a["title"]
        for a in authed_client(student).get("/api/v1/announcements/").json()["results"]
    ]
    assert set(titles) == {"همگانی", "گروه من"}


def test_admin_crud_and_permission(authed_client, admin, student, academic_graph):
    assert authed_client(student).post(
        "/api/v1/admin/announcements/", {"title": "x", "body": "y"}, format="json"
    ).status_code == 403

    client = authed_client(admin)
    created = client.post(
        "/api/v1/admin/announcements/",
        {
            "title": "اطلاعیه مهم",
            "body": "متن",
            "priority": AnnouncementPriority.HIGH,
            "term_id": academic_graph["term"].pk,
            "is_published": True,
            "published_at": timezone.now().isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["term"]["id"] == academic_graph["term"].pk

    listed = client.get("/api/v1/admin/announcements/", {"search": "مهم"})
    assert listed.status_code == 200
    assert len(listed.json()["results"]) == 1
