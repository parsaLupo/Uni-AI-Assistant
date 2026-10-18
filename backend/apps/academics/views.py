"""Academic-structure endpoints.

`/admin/{faculties,departments,terms}/` (ADMIN write, catalog in
docs/api/admin.md) plus the public `/terms/` read used by every
term-scoped screen.
"""

from __future__ import annotations

from django.db import IntegrityError
from rest_framework import viewsets

from apps.academics.models import AcademicTerm, Department, Faculty
from apps.academics.serializers import (
    AcademicTermSerializer,
    DepartmentSerializer,
    FacultySerializer,
)
from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import AuditableViewSetMixin
from apps.common.errors import CONFLICT, ApiError
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.persian import normalized_search


class AdminFacultyViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        qs = super().get_queryset()
        return normalized_search(qs, self.request.query_params.get("search"), "normalized_name")


class AdminDepartmentViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = Department.objects.select_related("faculty")
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        faculty = self.request.query_params.get("faculty")
        if faculty and faculty.isdigit():
            qs = qs.filter(faculty_id=int(faculty))
        return normalized_search(qs, self.request.query_params.get("search"), "normalized_name")

    def perform_destroy(self, instance):
        if instance.courses.exists() or instance.professors.exists():
            raise ApiError(
                CONFLICT,
                "گروه دارای درس یا استاد است و قابل حذف نیست.",
                http_status=409,
            )
        super().perform_destroy(instance)


class AdminTermViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]  # terms are never deleted

    def get_queryset(self):
        qs = super().get_queryset()
        is_current = self.request.query_params.get("is_current")
        if is_current is not None:
            qs = qs.filter(is_current=is_current.lower() in {"1", "true", "yes"})
        return qs

    def perform_update(self, serializer):
        # docs/api/admin.md: a historical term is immutable — a new academic
        # year creates a new AcademicTerm, never edits an old one (D4).
        if serializer.instance.is_past:
            raise ApiError(
                CONFLICT,
                "ترم گذشته تاریخی است و قابل ویرایش نیست؛ سال جدید با ترم جدید ساخته می‌شود.",
                http_status=409,
            )
        # A single current term is a DB constraint — translate its violation
        # into the documented 409 instead of a 500.
        try:
            super().perform_update(serializer)
        except IntegrityError as exc:
            raise ApiError(
                CONFLICT,
                "هم‌اکنون یک ترم جاری وجود دارد؛ ابتدا ترم فعلی را غیرجاری کنید.",
                http_status=409,
            ) from exc


class TermViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public term list/detail (docs/04 section 6)."""

    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
