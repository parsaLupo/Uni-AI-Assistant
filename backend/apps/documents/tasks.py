"""Background ingestion tasks for documents (ADR-011)."""

from __future__ import annotations

import logging

from django.utils import timezone

from apps.documents.models import Document, DocumentStatus
from apps.documents.storage import get_storage_adapter
from apps.rag.ingestion import ingest_document
from celery import shared_task

logger = logging.getLogger("app.ingestion")
metrics_logger = logging.getLogger("app.metrics")


def _transition(document: Document, status: str, **fields) -> None:
    document.status = status
    for key, value in fields.items():
        setattr(document, key, value)
    document.save(update_fields=["status", *fields.keys(), "updated_at"])


@shared_task(
    bind=True,
    name="documents.process_document",
    max_retries=3,
    default_retry_delay=10,
)
def process_document(self, document_id: int, idempotency_key: str | None = None) -> dict:
    started = timezone.now()
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.error("document_not_found document_id=%s", document_id)
        return {"document_id": document_id, "status": "missing"}

    if document.status in {DocumentStatus.INDEXED, DocumentStatus.ACTIVE}:
        logger.info("document_already_processed document_id=%s", document_id)
        return {"document_id": document_id, "status": document.status}

    adapter = get_storage_adapter()
    attempt = (document.attempt_count or 0) + 1
    document.attempt_count = attempt
    document.save(update_fields=["attempt_count", "updated_at"])

    try:
        logger.info("ingestion_stage stage=validating document_id=%s", document_id)
        _transition(document, DocumentStatus.VALIDATING)
        if not adapter.exists(document.storage_key):
            raise ValueError("stored file is missing")
        data = adapter.read(document.storage_key)
        if not data.startswith(b"%PDF"):
            raise ValueError("stored file is not a valid PDF")
        if b"/Encrypt" in data[:65536]:
            raise ValueError("encrypted PDF is not supported")
        if idempotency_key and document.checksum and idempotency_key != document.checksum:
            raise ValueError("checksum mismatch")

        logger.info("ingestion_stage stage=processing document_id=%s", document_id)
        result = ingest_document(document_id)
        duration_ms = int((timezone.now() - started).total_seconds() * 1000)
        metrics_logger.info(
            "ingestion_metric",
            extra={
                "event": "ingestion_completed",
                "document_id": document_id,
                "stage": "active",
                "attempt": attempt,
                "duration_ms": duration_ms,
                "chunk_count": result.get("chunk_count", 0),
            },
        )
        return {"document_id": document_id, "status": result.get("status", DocumentStatus.ACTIVE)}
    except Exception as exc:  # noqa: BLE001
        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            document = None
        failure_stage = "processing"
        if document is not None:
            document.status = DocumentStatus.FAILED
            document.processing_error = str(exc)
            document.failure_stage = failure_stage
            document.save(
                update_fields=["status", "processing_error", "failure_stage", "updated_at"]
            )
        logger.exception("ingestion_failed document_id=%s stage=%s", document_id, failure_stage)
        metrics_logger.info(
            "ingestion_metric",
            extra={
                "event": "ingestion_failed",
                "document_id": document_id,
                "stage": failure_stage,
                "attempt": attempt,
            },
        )
        if attempt < 3 and not isinstance(exc, ValueError):
            raise self.retry(exc=exc, countdown=min(60, 2 ** attempt)) from exc
        return {"document_id": document_id, "status": DocumentStatus.FAILED}

