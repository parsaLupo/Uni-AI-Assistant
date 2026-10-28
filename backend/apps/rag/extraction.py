"""PDF text extraction with page boundaries (Phase 08)."""

from __future__ import annotations

import io
from typing import Any

from pypdf import PdfReader


def extract_pdf_pages(data: bytes) -> list[dict[str, Any]]:
    """Extract text per page.

    Each entry has ``page_number``, ``text`` and ``supported``. A page is
    marked ``supported=False`` when no text could be extracted (scanned/OCR-less)
    so callers can report the gap instead of indexing noise (pipeline.md P-02).
    """
    if not data:
        raise ValueError("empty document")
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"could not read PDF: {exc}") from exc

    if getattr(reader, "is_encrypted", False):
        raise ValueError("encrypted PDF is not supported")

    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = ""
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            text = ""
        pages.append(
            {
                "page_number": index,
                "text": text,
                "supported": bool((text or "").strip()),
            }
        )
    return pages
