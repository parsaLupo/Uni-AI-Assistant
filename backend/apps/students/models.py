"""Student profile and enrollment (docs/03 section 3).

Onboarding collects the student's university code and major; `Enrollment`
doubles as the student's term planner: a `PLANNED` row is an item the student
put into their own planner, `ENROLLED` and the grade states are the
administratively managed record. One row per (student, offering) — the
planner cannot double-add a course, and formal enrollment cannot duplicate it.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.courses.models import CourseOffering


class DegreeLevel(models.TextChoices):
    BACHELOR = "BACHELOR", "کارشناسی"
    MASTER = "MASTER", "کارشناسی ارشد"
    PHD = "PHD", "دکتری"


class StudentProfile(models.Model):
    """Academic attributes of a student user; completed via onboarding."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    # «کد دانشجویی» — null until onboarding supplies it (unique among filled rows).
    student_number = models.CharField(max_length=16, unique=True, null=True, blank=True)
    faculty = models.ForeignKey(
        "academics.Faculty",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
    )
    # The student's «major» — chosen during onboarding.
    department = models.ForeignKey(
        "academics.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
    )
    degree_level = models.CharField(
        max_length=16, choices=DegreeLevel.choices, blank=True, default=""
    )
    entry_year = models.CharField(max_length=9, blank=True)  # Jalali «سال ورود»
    current_term_number = models.PositiveSmallIntegerField(null=True, blank=True)
    current_gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self) -> str:
        return self.student_number or self.user.email

    @property
    def onboarding_complete(self) -> bool:
        return bool(self.student_number and self.department_id)


class EnrollmentStatus(models.TextChoices):
    PLANNED = "PLANNED", "در برنامه‌ریزی"  # student's planner item (Phase 04)
    ENROLLED = "ENROLLED", "ثبت‌شده"
    PASSED = "PASSED", "قبول"
    FAILED = "FAILED", "مردود"
    DROPPED = "DROPPED", "حذف‌شده"
    WITHDRAWN = "WITHDRAWN", "انصراف‌داده"

    @classmethod
    def gradeable(cls) -> set[str]:
        """Statuses that may carry a grade."""
        return {cls.PASSED, cls.FAILED}


class Enrollment(models.Model):
    """A student's relation to one offering (planner row or graded record)."""

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="enrollments"
    )
    course_offering = models.ForeignKey(
        CourseOffering, on_delete=models.PROTECT, related_name="enrollments"
    )
    status = models.CharField(
        max_length=16, choices=EnrollmentStatus.choices, default=EnrollmentStatus.PLANNED
    )
    # 0–20 scale (OA-12 assumption; 4 digits = "20.00").
    grade = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-enrolled_at"]
        indexes = [
            # docs/03 section 4: "my enrollments this term" / "by status".
            models.Index(fields=["student", "status"], name="enrollment_student_status_idx"),
        ]
        constraints = [
            # docs/03 section 6: one enrollment per student per offering —
            # the planner cannot add the same section twice either.
            models.UniqueConstraint(
                fields=["student", "course_offering"], name="uniq_enrollment_student_offering"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} -> {self.course_offering} ({self.status})"

    def clean(self):
        errors = {}
        if (
            self.grade is not None
            and self.status_id
            and self.status not in EnrollmentStatus.gradeable()
        ):
            errors["grade"] = "نمره فقط برای وضعیت قبول/مردود مجاز است."
        if self.status_id and self.status in EnrollmentStatus.gradeable() and self.grade is None:
            errors["grade"] = "برای وضعیت قبول/مردود، نمره الزامی است."
        if errors:
            raise ValidationError(errors)
