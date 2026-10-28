"""Document ingestion pipeline (Phase 08)."""

from __future__ import annotations

import logging
import time

from django.db import transaction

from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.documents.storage import get_storage_adapter
from apps.rag.chunking import chunk_pages
from apps.rag.cleaning import clean_pages
from apps.rag.embeddings import embed_with_retry, get_embedding_provider
from apps.rag.extraction import extract_pdf_pages
from apps.rag.normalize import normalize_persian

logger = logging.getLogger("app.ingestion")
metrics_logger = logging.getLogger("app.metrics")


def _transition(document: Document, status: str, **fields) -> None:
    document.status = status
    for key, value in fields.items():
        setattr(document, key, value)
    document.save(update_fields=["status", *fields.keys(), "updated_at"])


def ingest_document(document_id: int) -> dict:
    started = time.monotonic()
    document = Document.objects.get(pk=document_id)
    adapter = get_storage_adapter()

    if not adapter.exists(document.storage_key):
        raise ValueError("stored file is missing")

    data = adapter.read(document.storage_key)
    if not data.startswith(b"%PDF"):
        raise ValueError("stored file is not a valid PDF")

    _transition(document, DocumentStatus.VALIDATING)
    pages = extract_pdf_pages(data)
    cleaned = clean_pages(pages)
    supported_pages = [page for page in cleaned if page.get("supported")]
    if not supported_pages:
        raise ValueError("no extractable text found; scanned pages are unsupported")

    _transition(document, DocumentStatus.PROCESSING, processing_error="", failure_stage="")

    chunks = chunk_pages(supported_pages)
    if not chunks:
        raise ValueError("chunking produced no chunks")

    provider = get_embedding_provider()
    normalized_texts = [normalize_persian(chunk["content"]) for chunk in chunks]
    embeddings = embed_with_retry(provider, normalized_texts)

    if any(len(embedding) != provider.dimension for embedding in embeddings):
        raise ValueError("embedding dimension mismatch")

    with transaction.atomic():
        document.chunks.all().delete()
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            DocumentChunk.objects.create(
                document=document,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                normalized_content=normalize_persian(chunk["content"]),
                page_number=chunk.get("page_number"),
                section_title=chunk.get("section_title", "") or "",
                token_count=chunk.get("token_count", 0),
                embedding=embedding,
                embedding_model=getattr(provider, "model_id", ""),
                embedding_dimension=getattr(provider, "dimension", 0),
                metadata={
                    "supported_pages": len(supported_pages),
                    "total_pages": len(pages),
                },
            )

    duration_ms = int((time.monotonic() - started) * 1000)
    metrics_logger.info(
        "ingestion_metric",
        extra={
            "event": "ingestion_indexed",
            "document_id": document.id,
            "stage": "indexed",
            "chunk_count": len(chunks),
            "token_count": sum(chunk.get("token_count", 0) for chunk in chunks),
            "duration_ms": duration_ms,
            "embedding_model": getattr(provider, "model_id", ""),
        },
    )

    # Indexing complete; activation remains an explicit admin action (Phase 07).
    document.status = DocumentStatus.INDEXED
    document.processing_error = ""
    document.failure_stage = ""
    document.save(update_fields=["status", "processing_error", "failure_stage", "updated_at"])
    return {
        "document_id": document.id,
        "status": document.status,
        "chunk_count": len(chunks),
    }
