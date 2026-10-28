"""Page-aware chunking (Phase 08)."""

from __future__ import annotations

import re
from typing import Any

_SENTENCE_RE = re.compile(r"(?<=[\.؟!؛\n])\s+")
_HEADING_RE = re.compile(r"^(?:\d+[\.\-)]?\s+|[^\.\n]{1,80}:)$")


def count_tokens(text: str | None) -> int:
    if not text:
        return 0
    # Approximate token count for Persian/English text.
    return max(1, len(text.split()))


def _split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = _SENTENCE_RE.split(text)
    return [part.strip() for part in parts if part.strip()]


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 100:
        return False
    return bool(_HEADING_RE.match(line)) or line.endswith(":")


def chunk_pages(
    pages: list[dict[str, Any]],
    target_tokens: int = 900,
    overlap_tokens: int = 120,
) -> list[dict[str, Any]]:
    """Chunk cleaned pages into coherent chunks with metadata."""
    chunks: list[dict[str, Any]] = []
    global_index = 0

    for page in pages:
        if not page.get("supported", True):
            continue
        text = page.get("text") or ""
        if not text.strip():
            continue

        section_title = ""
        sentences: list[str] = []
        for line in text.splitlines():
            if _is_heading(line):
                section_title = line.strip()
                continue
            sentences.extend(_split_sentences(line))

        if not sentences:
            sentences = [text]

        current: list[str] = []
        current_tokens = 0

        def finalize() -> None:  # noqa: B023
            nonlocal global_index, current, current_tokens
            if not current:
                return
            content = " ".join(current).strip()
            if not content:
                current = []
                current_tokens = 0
                return
            chunks.append(
                {
                    "chunk_index": global_index,
                    "content": content,
                    "page_number": page.get("page_number"),  # noqa: B023
                    "section_title": section_title,  # noqa: B023
                    "token_count": count_tokens(content),
                }
            )
            global_index += 1
            # Overlap: keep trailing sentences within the budget.
            overlap: list[str] = []
            overlap_tokens_used = 0
            for sentence in reversed(current):
                sentence_tokens = count_tokens(sentence)
                if overlap_tokens_used + sentence_tokens > overlap_tokens:
                    break
                overlap.insert(0, sentence)
                overlap_tokens_used += sentence_tokens
            current = list(overlap)
            current_tokens = overlap_tokens_used

        for sentence in sentences:
            sentence_tokens = count_tokens(sentence)
            if sentence_tokens > target_tokens:
                # Split an oversized sentence by words.
                words = sentence.split()
                for start in range(0, len(words), target_tokens):
                    piece = " ".join(words[start : start + target_tokens])
                    if current and current_tokens + count_tokens(piece) > target_tokens:
                        finalize()
                    current.append(piece)
                    current_tokens += count_tokens(piece)
                    if current_tokens >= target_tokens:
                        finalize()
                continue

            if current and current_tokens + sentence_tokens > target_tokens:
                finalize()
            current.append(sentence)
            current_tokens += sentence_tokens

        finalize()

    # Re-index sequentially in case overlap bookkeeping skipped numbers.
    for index, chunk in enumerate(chunks):
        chunk["chunk_index"] = index
    return chunks
