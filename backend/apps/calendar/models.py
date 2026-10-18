"""Academic calendar events (ERD: ACADEMIC_TERM ||--o{ ACADEMIC_EVENT)."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from apps.academics.models import AcademicTerm


class EventType(models.TextChoices):
    REGISTRATION = "REGISTRATION", "ثبت‌نام"
    EXAM_WEEK = "EXAM_WEEK", "هفته امتحانات"
    HOLIDAY = "HOLIDAY", "تعطیلات"
    CEREMONY = "CEREMONY", "مراسم"
    DEADLINE = "DEADLINE", "مهلت"
    OTHER = "OTHER", "سایر"


class AcademicEvent(models.Model):
    """A dated event scoped to a term (registration windows, exam weeks…)."""

    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=16, choices=EventType.choices, default=EventType.OTHER)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            # docs/03 section 4: calendar views read events of a term in order.
            models.Index(fields=["term", "starts_at"], name="event_term_starts_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(starts_at__lt=F("ends_at")), name="event_starts_before_ends"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.term})"
