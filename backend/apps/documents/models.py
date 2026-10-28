"""Document management (docs/03, 14: lifecycle Uploaded -> ... -> Archived)."""

from __future__ import annotations

from django.db import models

from apps.accounts.models import User


class DocumentStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "آپلود شده"
    VALIDATING = "VALIDATING", "در حال اعتبارسنجی"
    PROCESSING = "PROCESSING", "در حال پردازش"
    INDEXED = "INDEXED", "ایندکس شده"
    ACTIVE = "ACTIVE", "فعال"
    SUPERSEDED = "SUPERSEDED", "جایگزین شده"
    INACTIVE = "INACTIVE", "غیرفعال"
    ARCHIVED = "ARCHIVED", "آرشیو شده"
    FAILED = "FAILED", "ناموفق"

ALLOWED_STATUS_TRANSITIONS = {
    DocumentStatus.UPLOADED: {
        DocumentStatus.VALIDATING,
        DocumentStatus.PROCESSING,
        DocumentStatus.INACTIVE,
        DocumentStatus.FAILED,
        DocumentStatus.ARCHIVED,
        DocumentStatus.ACTIVE,
    },
    DocumentStatus.VALIDATING: {
        DocumentStatus.PROCESSING,
        DocumentStatus.FAILED,
        DocumentStatus.INACTIVE,
        DocumentStatus.ACTIVE,
    },
    DocumentStatus.PROCESSING: {
        DocumentStatus.INDEXED,
        DocumentStatus.FAILED,
        DocumentStatus.INACTIVE,
        DocumentStatus.ACTIVE,
    },
    DocumentStatus.INDEXED: {
        DocumentStatus.ACTIVE,
        DocumentStatus.INACTIVE,
        DocumentStatus.FAILED,
        DocumentStatus.ARCHIVED,
    },
    DocumentStatus.ACTIVE: {
        DocumentStatus.INACTIVE,
        DocumentStatus.SUPERSEDED,
        DocumentStatus.ARCHIVED,
    },
    DocumentStatus.SUPERSEDED: {DocumentStatus.ARCHIVED, DocumentStatus.INACTIVE},
    DocumentStatus.INACTIVE: {
        DocumentStatus.ACTIVE,
        DocumentStatus.ARCHIVED,
        DocumentStatus.UPLOADED,
    },
    DocumentStatus.FAILED: {DocumentStatus.UPLOADED},
    DocumentStatus.ARCHIVED: set(),
}


class Document(models.Model):
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=64, blank=True, default="")
    academic_year = models.CharField(max_length=32, blank=True, default="")
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.UPLOADED
    )
    checksum = models.CharField(max_length=64, blank=True, default="")
    storage_key = models.CharField(max_length=512, blank=True, default="")
    processing_error = models.TextField(blank=True, default="")
    failure_stage = models.CharField(max_length=64, blank=True, default="")
    attempt_count = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "academic_year"], name="document_status_year_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} v{self.version}"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in ALLOWED_STATUS_TRANSITIONS.get(self.status, set())
class DocumentChunk(models.Model):
    """A searchable chunk of a document (Phase 08)."""

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk_index = models.PositiveIntegerField(default=0)
    content = models.TextField()
    normalized_content = models.TextField(blank=True, default="")
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True, default="")
    token_count = models.PositiveIntegerField(default=0)
    embedding = models.JSONField(default=list, blank=True)
    embedding_model = models.CharField(max_length=128, blank=True, default="")
    embedding_dimension = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="document_chunk_index_uniq"
            )
        ]
        indexes = [
            models.Index(fields=["document", "chunk_index"], name="chunk_doc_idx_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.chunk_index}"
