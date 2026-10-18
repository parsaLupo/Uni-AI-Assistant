"""Announcements (docs/03 section 3, C-03/V-15: term + audience + expiry).

`term=NULL` means university-wide; `audience_faculty`/`audience_department`
NULL means everyone. List endpoints honour `is_published` and `expires_at`.
"""

from __future__ import annotations

from django.db import models

from apps.academics.models import AcademicTerm, Department, Faculty
from apps.common.persian import normalize_persian


class AnnouncementPriority(models.TextChoices):
    LOW = "LOW", "کم"
    NORMAL = "NORMAL", "عادی"
    HIGH = "HIGH", "زیاد"
    URGENT = "URGENT", "فوری"


class Announcement(models.Model):
    term = models.ForeignKey(
        AcademicTerm, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcements"
    )
    audience_faculty = models.ForeignKey(
        Faculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcements"
    )
    audience_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="announcements"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    priority = models.CharField(
        max_length=10, choices=AnnouncementPriority.choices, default=AnnouncementPriority.NORMAL
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    normalized_title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # docs/03 section 4: "active announcements" filters on both columns.
            models.Index(fields=["is_published", "expires_at"], name="announcement_active_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        self.normalized_title = normalize_persian(self.title)
        super().save(*args, **kwargs)
