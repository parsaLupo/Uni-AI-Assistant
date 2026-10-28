"""Retrieval service (Phase 08)."""

from __future__ import annotations

import logging
import math
import time
from datetime import date
from typing import Any

from django.utils import timezone

from apps.documents.models import DocumentChunk, DocumentStatus
from apps.rag.embeddings import get_embedding_provider
from apps.rag.normalize import normalize_persian

logger = logging.getLogger("app.retrieval")


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


class RetrievalService:
    def __init__(
        self,
        provider=None,
        top_k: int = 5,
        threshold: float = 0.2,
    ):
        self.provider = provider or get_embedding_provider()
        self.top_k = top_k
        self.threshold = threshold

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        started = time.monotonic()
        top_k = top_k or self.top_k
        threshold = self.threshold if threshold is None else threshold
        filters = filters or {}

        normalized_query = normalize_persian(query)
        query_vector = self.provider.embed([normalized_query])[0]

        qs = DocumentChunk.objects.select_related("document").filter(
            document__status=DocumentStatus.ACTIVE
        )

        document_type = filters.get("document_type")
        if document_type:
            qs = qs.filter(document__document_type=document_type)

        academic_year = filters.get("academic_year")
        if academic_year:
            qs = qs.filter(document__academic_year=academic_year)

        effective_on = filters.get("effective_on")
        if effective_on is None:
            effective_on = date.today() if False else None
        # Keep effective-period filtering optional and explicit.
        if filters.get("respect_effective_period"):
            from django.db.models import Q

            today = timezone.now().date()
            qs = qs.filter(document__effective_from__lte=today).filter(
                Q(document__effective_to__isnull=True)
                | Q(document__effective_to__gte=today)
            )

        results: list[dict[str, Any]] = []
        for chunk in qs:
            embedding = chunk.embedding or []
            if not embedding:
                continue
            if len(embedding) != len(query_vector):
                logger.warning(
                    "embedding_dimension_mismatch chunk_id=%s expected=%s actual=%s",
                    chunk.id,
                    len(query_vector),
                    len(embedding),
                )
                continue
            score = _cosine(query_vector, embedding)
            if score < threshold:
                continue
            doc = chunk.document
            results.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": doc.id,
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "academic_year": doc.academic_year,
                    "status": doc.status,
                    "page_number": chunk.page_number,
                    "section_title": chunk.section_title,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "normalized_content": chunk.normalized_content,
                    "embedding_model": chunk.embedding_model,
                    "score": score,
                    "label": doc.title,
                }
            )

        results.sort(key=lambda item: item["score"], reverse=True)
        results = results[:top_k]

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "retrieval_complete query_len=%s results=%s duration_ms=%s",
            len(normalized_query),
            len(results),
            duration_ms,
        )
        return results
