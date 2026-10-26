"""Document endpoints (admin-only)."""

from __future__ import annotations

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import AuditableViewSetMixin
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.documents.models import Document, DocumentStatus
from apps.documents.serializers import DocumentSerializer


class AdminDocumentViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = Document.objects.select_related("uploaded_by")
    serializer_class = DocumentSerializer
    permission_classes = [IsAdmin]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        st = params.get("status")
        if st:
            qs = qs.filter(status=st)
        dtype = params.get("document_type")
        if dtype:
            qs = qs.filter(document_type=dtype)
        year = params.get("academic_year")
        if year:
            qs = qs.filter(academic_year=year)
        search = params.get("search")
        if search:
            qs = qs.filter(title__icontains=search)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED, headers=headers)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        doc = self.get_object()
        doc.status = DocumentStatus.UPLOADED
        doc.processing_error = ""
        doc.failure_stage = ""
        doc.attempt_count = (doc.attempt_count or 0) + 1
        doc.save(update_fields=["status", "processing_error", "failure_stage", "attempt_count", "updated_at"])
        from apps.analytics.audit import record_audit

        record_audit(request.user, "RETRY", doc)
        return Response(self.get_serializer(doc).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        doc = self.get_object()
        doc.status = DocumentStatus.ACTIVE
        doc.save(update_fields=["status", "updated_at"])
        Document.objects.filter(
            title=doc.title, document_type=doc.document_type
        ).exclude(pk=doc.pk).filter(status=DocumentStatus.ACTIVE).update(
            status=DocumentStatus.SUPERSEDED
        )
        from apps.analytics.audit import record_audit

        record_audit(request.user, "UPDATE", doc)
        return Response(self.get_serializer(doc).data)