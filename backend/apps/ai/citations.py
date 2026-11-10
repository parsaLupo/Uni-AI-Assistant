"""Citation validation for Phase 09."""

from __future__ import annotations

import re


class CitationService:
    _CITATION_RE = re.compile(r"\[(\d+)\]")
    # Groq native citation footers like 【1†L14-L15】 — remove entirely since they
    # reference the provider's internal line numbers, not our document chunks.
    _GROQ_CITATION_RE = re.compile(r"【\d+†L\d+(?:-L\d+)?】")

    def sanitize(self, answer: str) -> str:
        """Remove control characters without corrupting Persian text or citations."""
        if not answer:
            return ""
        return "".join(
            char for char in answer
            if char in "\n\t" or (ord(char) >= 32 and not (0x7F <= ord(char) <= 0x9F))
        )

    def validate(self, answer: str, sources: list[dict]) -> str:
        """Remove citation markers that do not point to a supplied source."""
        answer = self.sanitize(answer or "")
        # Strip Groq's internal citation footers unconditionally.
        answer = self._GROQ_CITATION_RE.sub("", answer)

        def _replace(match: re.Match[str]) -> str:
            index = int(match.group(1))
            if 1 <= index <= len(sources):
                return match.group(0)
            return ""

        return self._CITATION_RE.sub(_replace, answer)
