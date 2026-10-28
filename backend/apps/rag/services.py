"""Convenience re-exports for RAG services."""

from apps.rag.chunking import chunk_pages, count_tokens
from apps.rag.cleaning import clean_pages, clean_text
from apps.rag.embeddings import embed_with_retry, get_embedding_provider
from apps.rag.extraction import extract_pdf_pages
from apps.rag.ingestion import ingest_document
from apps.rag.normalize import normalize_persian
from apps.rag.retrieval import RetrievalService

__all__ = [
    "chunk_pages",
    "clean_pages",
    "clean_text",
    "count_tokens",
    "embed_with_retry",
    "extract_pdf_pages",
    "get_embedding_provider",
    "ingest_document",
    "normalize_persian",
    "RetrievalService",
]
