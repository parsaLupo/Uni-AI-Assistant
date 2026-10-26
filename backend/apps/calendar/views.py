"""Academic calendar endpoints (admin CRUD + public read)."""

from __future__ import annotations

from rest_framework import viewsets

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import AuditableViewSetMixin
from apps.calendar.models import AcademicEvent
from apps.calendar.serializers import AcademicEventSerializer
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin


def _filter_events(qs, params):
    term = params.get("term")
    if term == "current":
        qs = qs.filter(term__is_current=True)
    elif term and term.isdigit():
        qs = qs.filter(term_id=int(term))
    event_type = params.get("event_type")
    if event_type:
        qs = qs.filter(event_type=event_type)
    return qs


class AdminAcademicEventViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = AcademicEvent.objects.select_related("term")
    serializer_class = AcademicEventSerializer
    permission_classes = [IsAdmin]
    ordering_fields = ["starts_at", "created_at"]
    ordering = ["starts_at"]

    def get_queryset(self):
        return _filter_events(super().get_queryset(), self.request.query_params)


class AcademicEventViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public calendar (docs/04 section 6) — published events only."""

    queryset = AcademicEvent.objects.filter(is_published=True).select_related("term")
    serializer_class = AcademicEventSerializer
    ordering_fields = ["starts_at", "created_at"]
    ordering = ["starts_at"]

    def get_queryset(self):
        qs = _filter_events(super().get_queryset(), self.request.query_params)
        from apps.common.scoping import student_department_id
        dept_id = student_department_id(self.request.user)
        if dept_id is not None:
            qs = qs.filter(term__offerings__course__department_id=dept_id).distinct()
        return qs
