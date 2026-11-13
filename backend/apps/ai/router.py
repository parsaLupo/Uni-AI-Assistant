"""Question router for Phase 09.

Classifies university questions into STRUCTURED, RAG, HYBRID, GENERAL,
or OUT_OF_SCOPE based on the actual information need, not just keywords.

STRUCTURED: Questions answerable directly from PostgreSQL records
  (exams, professors, credits, course codes, prerequisites, calendars).
RAG: Questions requiring unstructured university documents
  (regulations, policies, guidelines, official notices).
HYBRID: Questions requiring both structured data and document rules
  (eligibility based on passed courses + regulations).
GENERAL: General questions unrelated to university records.
OUT_OF_SCOPE: Questions outside the assistant's supported domain.
"""

from __future__ import annotations

import logging
import re

from apps.ai.modes import ExecutionMode
from apps.common.persian import normalize_persian

logger = logging.getLogger("app.ai.router")

UNIVERSITY_KEYWORDS = {
    "دانشگاه",
    "دانشجو",
    "درس",
    "ترم",
    "امتحان",
    "استاد",
    "واحد",
    "پیش‌نیاز",
    "پیش نیاز",
    "آیین‌نامه",
    "مقررات",
    "ثبت‌نام",
    "انصراف",
    "مرخصی",
    "مشروط",
    "ارائه",
    "سیلابس",
}

STRUCTURED_KEYWORDS = {
    "امتحان",
    "استاد",
    "واحد",
    "کردیت",
    "ارائه",
    "زمان",
    "تاریخ",
    "برنامه",
    "ظرفیت",
    "پیش‌نیاز",
    "پیش نیاز",
}

RAG_KEYWORDS = {
    "آیین‌نامه",
    "مقررات",
    "مشروط",
    "انصراف",
    "مرخصی",
    "ثبتنام",
    "شرایط",
    "قانون",
    "دستورالعمل",
    "راهنمای",
}

HYBRID_KEYWORDS = {
    "ترکیبی",
    "با توجه به",
    "دروس پاس‌شده",
    "میتونم بردارم",
    "تونم بردارم",
    "میتونم",
    "تونم",
    "پیشنهاد",
    "ثبتنام",
}

# Normalize all keyword sets so they match the normalized question text.
# This ensures ZWNJ/variant forms in keywords align with normalized input.
# Normalized keyword sets are pre-computed above.
_NORMALIZED_KEYWORD_SETS = []


def _normalize_keyword_set(keyword_set: set[str]) -> set[str]:
    return {normalize_persian(k) for k in keyword_set}


UNIVERSITY_KEYWORDS = _normalize_keyword_set(UNIVERSITY_KEYWORDS)
STRUCTURED_KEYWORDS = _normalize_keyword_set(STRUCTURED_KEYWORDS)
RAG_KEYWORDS = _normalize_keyword_set(RAG_KEYWORDS)
HYBRID_KEYWORDS = _normalize_keyword_set(HYBRID_KEYWORDS)

_NORMALIZED_KEYWORD_SETS.extend(
    [UNIVERSITY_KEYWORDS, STRUCTURED_KEYWORDS, RAG_KEYWORDS, HYBRID_KEYWORDS]
)

_VALID_MODES = {mode.value for mode in ExecutionMode}


class QuestionRouter:
    def __init__(self, provider=None) -> None:
        self.provider = provider

    def _deterministic_classify(self, question: str) -> tuple[ExecutionMode, str]:
        normalized = normalize_persian(question or "").lower()
        tokens = set(normalized.split())

        # Check HYBRID first — most specific.
        if any(keyword in normalized for keyword in HYBRID_KEYWORDS):
            return ExecutionMode.HYBRID, "hybrid keyword"

        # STRUCTURED: direct database facts.
        if any(keyword in normalized for keyword in STRUCTURED_KEYWORDS):
            return ExecutionMode.STRUCTURED, "structured keyword"

        # RAG: document-based regulations and policies.
        if any(keyword in normalized for keyword in RAG_KEYWORDS):
            return ExecutionMode.RAG, "rag keyword"

        if tokens & UNIVERSITY_KEYWORDS or any(k in normalized for k in UNIVERSITY_KEYWORDS):
            return ExecutionMode.RAG, "university keyword"

        if "چیست" in normalized or "توضیح" in normalized:
            return ExecutionMode.GENERAL, "general question"
        return ExecutionMode.OUT_OF_SCOPE, "no university keyword"

    def _model_classify(
        self, question: str, deterministic_mode: ExecutionMode
    ) -> ExecutionMode | None:
        if self.provider is None or deterministic_mode == ExecutionMode.OUT_OF_SCOPE:
            return None
        prompt = (
            "Classify the university assistant question into exactly one of: "
            "STRUCTURED, RAG, HYBRID, GENERAL, OUT_OF_SCOPE. "
            "Return only the mode name, with no explanation.\n"
            f"Question: {question}\n"
            f"Deterministic suggestion: {deterministic_mode.value}\n"
        )
        try:
            raw = self.provider.chat(prompt, timeout=5.0, max_retries=0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("model_routing_failed error=%s", type(exc).__name__)
            return None
        candidate = (raw or "").strip().upper()
        match = re.search(r"\b(STRUCTURED|RAG|HYBRID|GENERAL|OUT_OF_SCOPE)\b", candidate)
        if not match:
            logger.warning("model_routing_invalid response=%r", raw)
            return None
        return ExecutionMode(match.group(1))

    def classify(self, question: str) -> ExecutionMode:
        deterministic_mode, deterministic_reason = self._deterministic_classify(question)
        model_mode = self._model_classify(question, deterministic_mode)

        if model_mode is not None and deterministic_mode in {
            ExecutionMode.GENERAL,
        }:
            final_mode = model_mode
            basis = "model-assisted override for ambiguous deterministic result"
        elif model_mode is not None and model_mode == deterministic_mode:
            final_mode = deterministic_mode
            basis = "deterministic and model agreement"
        else:
            final_mode = deterministic_mode
            basis = deterministic_reason

        logger.info(
            "question_routed deterministic=%s model=%s final=%s basis=%s question_len=%s",
            deterministic_mode.value,
            model_mode.value if model_mode is not None else "unavailable",
            final_mode.value,
            basis,
            len(normalize_persian(question or "")),
        )
        return final_mode
