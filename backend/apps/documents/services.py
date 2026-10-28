"""Document application services (enqueue, audit orchestration)."""

from __future__ import annotations

from apps.documents.models import Document


def enqueue_document_processing(document: Document):
    """Schedule background ingestion for *document* and return the async result."""
    from apps.documents.tasks import process_document

    return process_document.delay(
        document.id,
        idempotency_key=document.checksum,
    )
