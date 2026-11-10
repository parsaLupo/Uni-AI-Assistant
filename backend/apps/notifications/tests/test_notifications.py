"""Phase 12 acceptance criteria, tested end-to-end via the API:

- Notifications are user-scoped (a student can never read another user's row).
- Read state persists (read_at set, unread badge decrements).
- Expired items never appear as active.
- Announcements fan out into per-user copies on publish (idempotent).

All authorisation is queryset-scoped, exactly like the planner contract:
another user's pk is a 404, never a 403.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.announcements.models import Announcement
from apps.professors.models import Professor
from apps.students.models import StudentProfile

pytestmark = pytest.mark.django_db

NOTIFICATIONS = "/api/v1/notifications/"
UNREAD_COUNT = f"{NOTIFICATIONS}unread-count/"
MARK_ALL_READ = f"{NOTIFICATIONS}mark-all-read/"


def _publish(title: str = "اطلاعیه مهم", **kwargs) -> Announcement:
    defaults = {
        "title": title,
        "body": "متن اطلاعیه",
        "is_published": True,
        "published_at": timezone.now(),
    }
    defaults.update(kwargs)
    return Announcement.objects.create(**defaults)


def _notify(user, title: str = "یادآوری", **kwargs):
    """Direct row creation (simulates any future trigger source)."""
    from apps.notifications.services import create_notification

    return create_notification(user=user, title=title, **kwargs)


def _user_rows(user):
    from apps.notifications.models import Notification

    return Notification.objects.filter(user=user)


# --- Fan-out (admin-created announcements surfaced as notifications) ---------


def test_published_announcement_fans_out_to_all_active_users(
    authed_client, student, student_profile, admin, professor_user
):
    from apps.notifications.services import announcement_recipients

    client = authed_client(admin)
    created = client.post(
        "/api/v1/admin/announcements/",
        {
            "title": "اطلاعیه مهم",
            "body": "متن اطلاعیه",
            "is_published": True,
            "published_at": timezone.now().isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201

    announcement = Announcement.objects.get(pk=created.json()["id"])
    # University-wide: every active user, student or not.
    assert {u.pk for u in announcement_recipients(announcement)} == {
        student.pk,
        admin.pk,
        professor_user.pk,
    }
    titles = [
        n["title"]
        for n in authed_client(student).get(NOTIFICATIONS).json()["results"]
    ]
    assert titles == ["اطلاعیه مهم"]

    # Drafts never fan out.
    client.post(
        "/api/v1/admin/announcements/",
        {
            "title": "پیش‌نویس",
            "body": "",
            "is_published": False,
        },
        format="json",
    )
    assert authed_client(admin).get(NOTIFICATIONS).json()["count"] == 1


def test_faculty_targeted_fans_out_to_faculty_students_and_profile_less_users(
    student, student_profile, professor_user, academic_graph
):
    # Professors exist as teaching staff; the notification fan-out treats the
    # *user* as profile-less (the feed rule for professors/admins).
    Professor.objects.create(
        department=academic_graph["department"],
        first_name="استاد",
        last_name="دیگر",
    )

    announcement = _publish(title="دانشکده", audience_faculty=academic_graph["faculty"])

    from apps.notifications.services import announcement_recipients

    recipients = {u.pk for u in announcement_recipients(announcement)}
    assert recipients == {student.pk, professor_user.pk}  # faculty student + profile-less


def test_department_targeted_excludes_profile_less_users_and_other_students(
    authed_client, student, student_profile, admin, professor_user, academic_graph
):
    from apps.accounts.models import User

    classmate = User.objects.create_user(
        email="mate@example.edu", password="Str0ng-Passw0rd!", role="STUDENT"
    )
    StudentProfile.objects.create(
        user=classmate,
        student_number="40422222",
        department=academic_graph["department"],
        faculty=academic_graph["faculty"],
    )

    created = authed_client(admin).post(
        "/api/v1/admin/announcements/",
        {
            "title": "گروهی",
            "body": "فقط گروه",
            "audience_department_id": academic_graph["department"].pk,
            "is_published": True,
            "published_at": timezone.now().isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201

    titles = [
        n["title"]
        for n in authed_client(student).get(NOTIFICATIONS).json()["results"]
    ]
    assert titles == ["گروهی"]
    assert _user_rows(professor_user).count() == 0  # profile-less user excluded
    assert _user_rows(classmate).count() == 1       # same department student included


def test_fan_out_is_idempotent_across_unpublish_and_republish(
    student, student_profile
):
    from apps.notifications.services import dispatch_announcement

    announcement = _publish()
    assert dispatch_announcement(announcement) == 1
    assert _user_rows(student).count() == 1

    # A re-dispatch of an already faned-out announcement creates nothing.
    assert dispatch_announcement(announcement) == 0
    assert _user_rows(student).count() == 1

    # Unpublish → republish (the performed update path) also never duplicates;
    # only published announcements fan out at all.
    announcement.is_published = False
    announcement.save()
    assert dispatch_announcement(announcement) == 0
    announcement.is_published = True
    announcement.save()
    assert dispatch_announcement(announcement) == 0
    assert _user_rows(student).count() == 1


# --- Scoping (AC: notifications are user-scoped; cross-user reads tested) ----


def test_list_and_detail_are_strictly_user_scoped(authed_client, student, admin):
    mine = _notify(student)
    theirs = _notify(admin)

    client = authed_client(student)
    payload = client.get(NOTIFICATIONS).json()
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == mine.pk

    # Another user's pk is a 404 (anti-enumeration, planner contract).
    response = client.post(f"{NOTIFICATIONS}{theirs.pk}/mark-read/")
    assert response.status_code == 404

    # The foreign row was not touched.
    theirs.refresh_from_db()
    assert theirs.is_read is False


def test_mark_read_of_unknown_pk_is_404(authed_client, student):
    client = authed_client(student)
    assert client.post(f"{NOTIFICATIONS}999999/mark-read/").status_code == 404


def test_read_state_persists_and_badge_decrements(authed_client, student):
    _notify(student, "اول")
    _notify(student, "دوم")
    client = authed_client(student)

    assert client.get(UNREAD_COUNT).json()["unread_count"] == 2

    row = client.get(NOTIFICATIONS).json()["results"][0]
    marked = client.post(f"{NOTIFICATIONS}{row['id']}/mark-read/")
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert marked.json()["read_at"]

    assert client.get(UNREAD_COUNT).json()["unread_count"] == 1

    reread = client.get(NOTIFICATIONS).json()["results"][0]
    assert reread["is_read"] is True


def test_mark_all_read(authed_client, student):
    _notify(student, "الف")
    _notify(student, "ب", type="DEADLINE")
    expired = _notify(student, "ج", expires_at=timezone.now() - timedelta(hours=1))
    client = authed_client(student)

    updated = client.post(MARK_ALL_READ).json()["updated"]
    assert updated == 2  # expired rows are not active, so untouched

    assert _user_rows(student).filter(expires_at__isnull=True, is_read=False).count() == 0
    expired.refresh_from_db()
    assert expired.is_read is False


def test_unread_filter(authed_client, student):
    read_row = _notify(student, "خوانده")
    read_row.is_read = True
    read_row.read_at = timezone.now()
    read_row.save()
    _notify(student, "ناخوانده")

    client = authed_client(student)
    payload = client.get(f"{NOTIFICATIONS}?unread=true").json()
    assert payload["count"] == 1
    assert payload["results"][0]["title"] == "ناخوانده"


# --- Expiry (AC: expired items never appear as active) -----------------------


def test_expired_items_hidden_from_list_and_badge(authed_client, student):
    _notify(student, "فعال")
    _notify(student, "منقضی", expires_at=timezone.now() - timedelta(minutes=5))
    _notify(student, "آینده", expires_at=timezone.now() + timedelta(days=30))

    client = authed_client(student)
    payload = client.get(NOTIFICATIONS).json()
    assert payload["count"] == 2
    titles = {n["title"] for n in payload["results"]}
    assert "منقضی" not in titles
    assert client.get(UNREAD_COUNT).json()["unread_count"] == 2


# --- Access control ----------------------------------------------------------


def test_unauthenticated_requests_rejected(api_client):
    assert api_client.get(NOTIFICATIONS).status_code == 401
    assert api_client.get(UNREAD_COUNT).status_code == 401
    assert api_client.post(MARK_ALL_READ).status_code == 401
    assert api_client.post(f"{NOTIFICATIONS}1/mark-read/").status_code == 401


def test_user_without_student_profile_lists_own_notifications(
    authed_client, professor_user
):
    _notify(professor_user, "برای استاد")
    payload = authed_client(professor_user).get(NOTIFICATIONS).json()
    assert payload["count"] == 1
    assert payload["results"][0]["title"] == "برای استاد"
