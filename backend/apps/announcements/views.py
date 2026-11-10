"""Announcement endpoints (admin CRUD + public feed with expiry semantics)."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import AuditableViewSetMixin
from apps.announcements.models import Announcement
from apps.announcements.serializers import AnnouncementSerializer
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.persian import normalized_search
from apps.notifications.services import dispatch_announcement


def _filter_announcements(qs, params):
    term = params.get("term")
    if term == "current":
        qs = qs.filter(term__is_current=True)
    elif term and term.isdigit():
        qs = qs.filter(term_id=int(term))
    elif term == "none":
        qs = qs.filter(term__isnull=True)
    return qs


class AdminAnnouncementViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = Announcement.objects.select_related(
        "term", "audience_faculty", "audience_department"
    )
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdmin]
    ordering_fields = ["created_at", "published_at", "expires_at", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _filter_announcements(super().get_queryset(), self.request.query_params)
        is_published = self.request.query_params.get("is_published")
        if is_published is not None:
            qs = qs.filter(is_published=is_published.lower() in {"1", "true", "yes"})
        return normalized_search(
            qs, self.request.query_params.get("search"), "normalized_title"
        )

    def perform_create(self, serializer):
        announcement = serializer.save()
        dispatch_announcement(announcement)

    def perform_update(self, serializer):
        was_published = serializer.instance.is_published
        announcement = serializer.save()
        if announcement.is_published and not was_published:
            dispatch_announcement(announcement)


class AnnouncementViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public feed: published, not yet expired, audience matching the caller.

    C-03: `term=NULL` = university-wide, audience NULLs = everyone. Expired
    rows disappear from the list (docs/api/admin.md: "expiry honoured by list
    endpoints").
    """

    serializer_class = AnnouncementSerializer
    ordering_fields = ["created_at", "published_at", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self):
        now = timezone.now()
        qs = Announcement.objects.filter(is_published=True).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )
        qs = _filter_announcements(qs, self.request.query_params)

        profile = getattr(self.request.user, "student_profile", None)
        if profile is None:
            # No student profile (professor/admin): rows not scoped to a department.
            audience_q = Q(audience_department__isnull=True)
        else:
            audience_q = (
                Q(audience_faculty__isnull=True, audience_department__isnull=True)
                | Q(audience_faculty=profile.faculty, audience_department__isnull=True)
                | Q(audience_department=profile.department)
            )
        return qs.filter(audience_q).select_related(
            "term", "audience_faculty", "audience_department"
        )
