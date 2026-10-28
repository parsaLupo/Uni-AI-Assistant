"""Text cleaning helpers (Phase 08)."""

from __future__ import annotations

import re
from collections import Counter


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    # Collapse runs of whitespace inside each line.
    lines = [re.sub(r"\s+", " ", line) for line in lines]
    return "\n".join(lines)


def _line_frequencies(pages_text: list[str]) -> Counter:
    counter: Counter = Counter()
    for text in pages_text:
        for line in {line.strip() for line in text.splitlines() if line.strip()}:
            counter[line] += 1
    return counter


def clean_pages(pages: list[dict]) -> list[dict]:
    """Clean per-page text and drop lines that repeat on most pages (headers/footers)."""
    cleaned = []
    texts = [page.get("text", "") or "" for page in pages]
    freq = _line_frequencies(texts)
    threshold = max(2, (len(texts) // 2) + 1)
    repeated = {line for line, count in freq.items() if count >= threshold}

    for page in pages:
        lines = list((page.get("text") or "").splitlines())
        kept = []
        for line in lines:
            stripped = line.strip()
            if stripped and stripped in repeated:
                continue
            kept.append(line)
        new_page = dict(page)
        new_page["text"] = clean_text("\n".join(kept))
        new_page["supported"] = bool((new_page["text"] or "").strip()) if page.get(
            "supported", True
        ) else False
        if page.get("supported") is False:
            new_page["supported"] = False
        cleaned.append(new_page)
    return cleaned
