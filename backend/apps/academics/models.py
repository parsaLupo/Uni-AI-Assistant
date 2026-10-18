"""Academic structure: faculties, departments, terms (docs/03 section 3).

Searchable names carry a `normalized_*` twin written at save time
(architecture.md C-05) so `?search=` survives ی/ي, ک/ك and نیم‌فاصله variants.
"""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from apps.common.persian import normalize_persian


class Faculty(models.Model):
    """A university faculty (دانشکده)."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=16, unique=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    normalized_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_persian(self.name)
        super().save(*args, **kwargs)


class Department(models.Model):
    """A department (گروه) inside a faculty — also the student's «major»."""

    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=16)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    normalized_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["faculty__name", "name"]
        constraints = [
            # docs/03 section 6: codes are referenced externally — unique per faculty.
            models.UniqueConstraint(
                fields=["faculty", "code"], name="uniq_department_code_per_faculty"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_persian(self.name)
        super().save(*args, **kwargs)


class TermSemester(models.TextChoices):
    FIRST = "FIRST", "نیمسال اول"
    SECOND = "SECOND", "نیمسال دوم"
    SUMMER = "SUMMER", "نیمسال تابستان"


class AcademicTerm(models.Model):
    """One academic term. Historical rows are immutable (docs/03 section 5)."""

    name = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=16)  # «۱۴۰۵-۱۴۰۶» / "1405-1406"
    semester_type = models.CharField(max_length=8, choices=TermSemester.choices)
    starts_at = models.DateField()
    ends_at = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at"]
        constraints = [
            # docs/03 section 6: "current term" drives default queries — at most one.
            models.UniqueConstraint(
                fields=["is_current"],
                condition=Q(is_current=True),
                name="uniq_current_academic_term",
            ),
            models.CheckConstraint(
                check=Q(starts_at__lt=F("ends_at")),
                name="academic_term_starts_before_ends",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_past(self) -> bool:
        from django.utils import timezone

        return self.ends_at < timezone.localdate()
