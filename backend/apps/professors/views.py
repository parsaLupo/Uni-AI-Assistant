"""Professor endpoints: /admin/professors/ + public /professors/."""

from __future__ import annotations

from rest_framework import viewsets

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import AuditableViewSetMixin
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.persian import normalized_search
from apps.professors.models import Professor
from apps.professors.serializers import ProfessorSerializer


def _filter_professors(qs, params, user=None):
    from apps.common.scoping import student_department_id
    from django.db.models import Q

    department = params.get("department")
    if department and department.isdigit():
        qs = qs.filter(department_id=int(department))
    is_active = params.get("is_active")
    if is_active is not None:
        qs = qs.filter(is_active=is_active.lower() in {"1", "true", "yes"})
    term = params.get("term")
    if term and term.isdigit():
        # CourseOffering.professor has related_name="offerings"; filtering on a
        # non-existent accessor would raise FieldError and answer 500.
        qs = qs.filter(offerings__term_id=int(term)).distinct()
    # Automatic department scoping for students: keep professors of the
    # student's own department plus those who teach a relevant course in
    # another department (do not drop cross-department teachers).
    dept_id = student_department_id(user)
    if dept_id is not None:
        qs = qs.filter(
            Q(department_id=dept_id) | Q(offerings__course__department_id=dept_id)
        ).distinct()
    return normalized_search(qs, params.get("search"), "normalized_name")


class AdminProfessorViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = Professor.objects.select_related("department")
    serializer_class = ProfessorSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["department", "is_active"]

    def get_queryset(self):
        return _filter_professors(super().get_queryset(), self.request.query_params, self.request.user)


class ProfessorViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public professor catalog (docs/04 section 6)."""

    queryset = Professor.objects.filter(is_active=True).select_related("department")
    serializer_class = ProfessorSerializer

    def get_queryset(self):
        return _filter_professors(super().get_queryset(), self.request.query_params, self.request.user)
