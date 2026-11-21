"""Document application services (enqueue, audit orchestration)."""

from __future__ import annotations

from apps.documents.models import Document


def enqueue_document_processing(document: Document, request_id: str | None = None):
    """Schedule background ingestion for *document* and return the async result.

    ``request_id`` is forwarded so the worker's ingestion logs can be joined
    with the HTTP request that triggered them (docs/12 section 4).
    """
    from apps.documents.tasks import process_document

    return process_document.delay(
        document.id,
        idempotency_key=document.checksum,
        request_id=request_id,
    )
