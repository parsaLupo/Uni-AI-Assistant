"""Document endpoints (admin-only)."""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import record_audit
from apps.common.errors import VALIDATION_ERROR, ApiError
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.throttles import UploadRateThrottle
from apps.documents.models import Document, DocumentStatus
from apps.documents.serializers import DocumentSerializer
from apps.documents.services import enqueue_document_processing


class AdminDocumentViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, viewsets.ModelViewSet
):
    queryset = Document.objects.select_related("uploaded_by")
    serializer_class = DocumentSerializer
    permission_classes = [IsAdmin]
    ordering = ["-created_at"]

    def get_throttles(self):
        # Phase 15 abuse control: the upload budget applies to `create` (and
        # the `retry` action, which re-enqueues processing) only — listing,
        # updating metadata and status changes stay unthrottled.
        if self.action in {"create", "retry"}:
            return [UploadRateThrottle()]
        return []

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

    def perform_create(self, serializer):
        instance = serializer.save()
        enqueue_document_processing(
            instance, request_id=getattr(self.request, "request_id", None)
        )
        record_audit(self.request.user, "CREATE", instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        record_audit(self.request.user, "UPDATE", instance)

    def perform_destroy(self, instance):
        record_audit(self.request.user, "DELETE", instance)
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        headers["Location"] = f"/api/v1/admin/documents/{serializer.data['id']}/"
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED, headers=headers)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        doc = self.get_object()
        if doc.status != DocumentStatus.FAILED:
            raise ApiError(
                VALIDATION_ERROR,
                "فقط اسناد ناموفق قابل تلاش مجدد هستند.",
                http_status=400,
            )
        doc.status = DocumentStatus.UPLOADED
        doc.processing_error = ""
        doc.failure_stage = ""
        doc.attempt_count = (doc.attempt_count or 0) + 1
        doc.save(
            update_fields=[
                "status",
                "processing_error",
                "failure_stage",
                "attempt_count",
                "updated_at",
            ]
        )
        enqueue_document_processing(doc, request_id=getattr(request, "request_id", None))
        record_audit(request.user, "RETRY", doc)
        return Response(self.get_serializer(doc).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        doc = self.get_object()
        if not doc.can_transition_to(DocumentStatus.ACTIVE):
            raise ApiError(VALIDATION_ERROR, "فعال‌سازی در این وضعیت مجاز نیست.", http_status=400)
        doc.status = DocumentStatus.ACTIVE
        doc.save(update_fields=["status", "updated_at"])
        Document.objects.filter(
            title=doc.title, document_type=doc.document_type
        ).exclude(pk=doc.pk).filter(status=DocumentStatus.ACTIVE).update(
            status=DocumentStatus.SUPERSEDED
        )
        record_audit(request.user, "UPDATE", doc)
        return Response(self.get_serializer(doc).data)
