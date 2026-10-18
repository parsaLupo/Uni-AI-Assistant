"""Professor entity (docs/03 section 3)."""

from __future__ import annotations

from django.db import models

from apps.academics.models import Department
from apps.common.persian import normalize_persian


class Professor(models.Model):
    """Teaching staff, employed by a department (ERD: DEPARTMENT ||--o{ PROFESSOR)."""

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="professors")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    # Data-driven free text (استاد/دانشیار/استادیار/مربی…) — not a closed enum,
    # because the source dataset (data/Professors.json) supplies Persian titles.
    academic_title = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    office = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    normalized_name = models.CharField(max_length=210, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_persian(f"{self.first_name} {self.last_name}")
        super().save(*args, **kwargs)
