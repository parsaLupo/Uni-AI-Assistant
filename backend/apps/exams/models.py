"""Exam entity (docs/03 section 3).

An exam belongs to a concrete *offering*, not to a course (docs/17): two
sections of the same course may sit different exams. One exam per offering is
enforced by the one-to-one relation itself (docs/03 section 6).
"""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from apps.courses.models import CourseOffering


class ExamStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "زمان‌بندی‌شده"
    CHANGED = "CHANGED", "تغییریافته"
    CANCELLED = "CANCELLED", "لغوشده"


class Exam(models.Model):
    """The exam of one offering, frozen once its term is history."""

    course_offering = models.OneToOneField(
        CourseOffering, on_delete=models.CASCADE, related_name="exam"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    classroom = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=12, choices=ExamStatus.choices, default=ExamStatus.SCHEDULED
    )
    last_updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(starts_at__lt=F("ends_at")), name="exam_starts_before_ends"
            ),
        ]

    def __str__(self) -> str:
        return f"امتحان {self.course_offering}"
