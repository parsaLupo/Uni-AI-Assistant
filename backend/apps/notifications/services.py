"""Notification fan-out service (Phase 12).

Business logic lives here, not in views (architecture.md section 3.1). The
service creates one *user-scoped* row per recipient: read state is private to
each user by construction (AC "notifications are scoped to a user").
Fan-out is idempotent through the ``(user, source_announcement)`` unique
constraint — a re-published announcement never duplicates rows
(``bulk_create(ignore_conflicts=True)``).

Recipients follow the announcement feed visibility exactly (C-03 /
`apps.announcements.views.AnnouncementViewSet.get_queryset`): department-
targeted rows go to that department's students; faculty-targeted rows go to the
faculty's students *and* every active user without a student profile
(professors/admins), matching the feed's audience predicate for profile-less
users; unrestricted announcements go to every active user.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.announcements.models import Announcement
from apps.notifications.models import Notification, NotificationType

User = get_user_model()

_BATCH_SIZE = 500


def announcement_recipients(announcement: Announcement):
    """Active users who would see *announcement* in the feed (C-03 semantics)."""
    qs = User.objects.filter(is_active=True)
    if announcement.audience_department_id is not None:
        return qs.filter(student_profile__department_id=announcement.audience_department_id)
    if announcement.audience_faculty_id is not None:
        # Feed rule for users without a student profile (professors/admins):
        # every announcement that is not department-scoped is visible, so a
        # faculty-targeted notice also reaches them.
        return qs.select_related("student_profile").filter(
            Q(student_profile__faculty=announcement.audience_faculty)
            | Q(student_profile__isnull=True)
        )
    return qs.select_related("student_profile")


def create_notification(
    *,
    user,
    title: str,
    body: str = "",
    type: str = NotificationType.SYSTEM,  # noqa: A002 — DRF-facing name
    link: str = "",
    expires_at=None,
    source_announcement: Announcement | None = None,
) -> Notification:
    """Single-row helper (e.g. for future deadline automation)."""
    return Notification.objects.create(
        user=user,
        type=type,
        title=title,
        body=body,
        link=link,
        expires_at=expires_at,
        source_announcement=source_announcement,
    )


def dispatch_announcement(announcement: Announcement) -> int:
    """Fan out one user-scoped copy of *announcement*; returns rows created.

    ``ignore_conflicts=True`` makes re-publishing safe under races: existing
    ``(user, source_announcement)`` pairs are skipped by the database.
    """
    # Do not resurrect notifications for announcements that were published and
    # then unpublished: only genuinely published rows fan out.
    if not announcement.is_published:
        return 0
    existing = set(
        Notification.objects.filter(source_announcement=announcement).values_list(
            "user_id", flat=True
        )
    )
    rows = [
        Notification(
            user=user,
            type=NotificationType.ANNOUNCEMENT,
            title=announcement.title,
            body=announcement.body[:2000],
            link="/announcements",
            expires_at=announcement.expires_at,
            source_announcement=announcement,
        )
        for user in announcement_recipients(announcement)
        if user.pk not in existing
    ]
    Notification.objects.bulk_create(rows, batch_size=_BATCH_SIZE, ignore_conflicts=True)
    return len(rows)


def active_notifications(user):
    """Non-expired notifications of *user*, newest first."""
    now = timezone.now()
    return Notification.objects.filter(user=user).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )


def unread_count(user) -> int:
    return active_notifications(user).filter(is_read=False).count()
