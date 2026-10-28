"""Embedding provider adapter (Phase 08)."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import time
from typing import Protocol

logger = logging.getLogger("app.ingestion")


class EmbeddingProvider(Protocol):
    model_id: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalHashEmbeddingProvider:
    """Deterministic, dependency-free embedding provider for tests/offline use."""

    def __init__(self, model_id: str | None = None, dimension: int | None = None):
        self.model_id = model_id or os.environ.get(
            "EMBEDDING_MODEL", "local-hash-embedding-v1"
        )
        self.dimension = dimension or int(os.environ.get("EMBEDDING_DIMENSION", "64"))

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            for token in (text or "").split():
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                for offset in range(0, len(digest), 4):
                    index = int.from_bytes(digest[offset : offset + 4], "big") % self.dimension
                    vector[index] += 1.0
            # L2 normalize.
            norm = math.sqrt(sum(value * value for value in vector))
            if norm:
                vector = [value / norm for value in vector]
            vectors.append(vector)
        return vectors


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = os.environ.get("EMBEDDING_PROVIDER", "local").strip().lower()
    if provider_name in {"", "local", "hash", "deterministic"}:
        return LocalHashEmbeddingProvider()
    # Unknown providers fall back to the local adapter rather than crashing.
    logger.warning("unknown_embedding_provider name=%s fallback=local", provider_name)
    return LocalHashEmbeddingProvider()


def embed_with_retry(
    provider: EmbeddingProvider,
    texts: list[str],
    batch_size: int = 32,
    max_retries: int = 3,
) -> list[list[float]]:
    """Embed *texts* in batches with retry/backoff and cost accounting."""
    if not texts:
        return []

    results: list[list[float]] = []
    total_tokens = sum(len(text.split()) for text in texts)
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                batch_vectors = provider.embed(batch)
                if any(len(vector) != provider.dimension for vector in batch_vectors):
                    raise ValueError("embedding dimension mismatch")
                results.extend(batch_vectors)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.warning(
                    "embedding_batch_failed attempt=%s/%s error=%s",
                    attempt,
                    max_retries,
                    exc,
                )
                if attempt < max_retries:
                    time.sleep(min(2 ** attempt, 8))
        if last_exc is not None:
            raise last_exc

    logger.info(
        "embedding_complete model=%s dimension=%s chunks=%s tokens=%s",
        getattr(provider, "model_id", "unknown"),
        getattr(provider, "dimension", 0),
        len(results),
        total_tokens,
    )
    return results
