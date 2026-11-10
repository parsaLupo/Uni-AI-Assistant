"""Notification model (Phase 12, full checklist: type/title/body/link, read
state, expiry).

The model is deliberately minimal: one row per recipient. A fan-out copy is
not a duplicate university fact in the docs/03 sense — the per-user read
state is exactly the documented reason (docs/03 section 3: read state belongs
to the recipient, not the source record).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.announcements.models import Announcement


class NotificationType(models.TextChoices):
    ANNOUNCEMENT = "ANNOUNCEMENT", "اطلاعیه"
    DEADLINE = "DEADLINE", "مهلت"
    EXAM = "EXAM", "امتحان"
    SYSTEM = "SYSTEM", "سیستمی"


class Notification(models.Model):
    """One recipient's copy of a notification (per-user read state)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=16, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    # App path of the related surface (e.g. "/announcements") — never injected,
    # only routing for the frontend.
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    # Traceability + idempotent fan-out: re-publishing an announcement must
    # never create a second notification for the same user.
    source_announcement = models.ForeignKey(
        Announcement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # "active (non-expired, unread) for user X" is the hot query:
            # the list endpoint filters both columns.
            models.Index(fields=["user", "is_read"], name="notif_user_read_idx"),
            models.Index(fields=["user", "expires_at"], name="notif_user_expiry_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source_announcement"],
                condition=Q(source_announcement__isnull=False),
                name="uniq_user_source_announcement",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.title}"
