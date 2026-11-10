"""Answer formatting helpers for Phase 09."""

from __future__ import annotations

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "شواهد رسمی کافی برای پاسخ به این پرسش یافت نشد. "
    "لطفاً سؤال را دقیق‌تر مطرح کنید یا به منابع رسمی مراجعه کنید."
)


class AnswerFormatter:
    def format(self, raw_answer: str, sources: list[dict], *, insufficient: bool = False) -> str:
        if insufficient:
            return INSUFFICIENT_EVIDENCE_MESSAGE
        answer = (raw_answer or "").strip()
        if not answer:
            raise ValueError("empty provider output")
        return answer
