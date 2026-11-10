"""Phase 11 — explanation layer for the deterministic selection engine.

AGENTS.md section 8: "The LLM must never independently decide course
eligibility. Eligibility is calculated by deterministic backend rules; the
LLM may explain the result." This service therefore treats the engine's
serialised decision (``SelectionDecision.from_dict``) as the *only* input and
produces the user-facing Persian prose in one of two ways:

* ``composed`` — a purely deterministic paraphrase built from the decision's
  reason codes and credit totals. Never fails, never invents.
* ``llm`` — the provider's paraphrase of the engine JSON, accepted only when
  it does not contradict the engine verdict (docs/18 "Course selection rule").

Contradiction detection is lexical, not prompt-side: every output claiming the
opposite of ``decision.eligible`` — or arriving from a failing provider — is
discarded and replaced by the composed text. A test feeds a deliberately
contradicting provider to prove override is impossible.
"""

from __future__ import annotations

import json
from typing import Any

from apps.common.persian import normalize_persian
from apps.students.course_selection import SelectionDecision

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(value: Any) -> str:
    return str(value).translate(_PERSIAN_DIGITS)


# Verdict claims, compared on normalize_persian() forms so ZWNJ/Arabic-yeh
# variants cannot dodge detection ("مجاز‌نیست" ≈ "مجاز نیست"). Ineligible
# claims are matched against the raw normalized text; eligible claims are
# matched after negation prefixes (نمی، غیر، بدون) are stripped, so a correct
# paraphrase like «این درس مجاز نیست» is never misread as «مجاز».
_PHRASES_INELIGIBLE = (
    "مجاز نیست",
    "مجاز نمیباشد",
    "غیرمجاز",
    "نمی توانید",
    "نمیتوان",
    "قابل برداشتن نیست",
    "امکان انتخاب ندارد",
    "رد میشود",
)
_PHRASES_ELIGIBLE = (
    "مجاز است",
    "مجاز میباشد",
    "مجازید",
    "می توانید",
    "قابل برداشتن است",
    "امکان انتخاب دارد",
    "بله",
)
_NEGATION_PREFIXES = ("نمی", "غیر", "بدون")


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """Normalized substring match; *haystack* must already be normalized."""
    return normalize_persian(phrase) in haystack


class SelectionExplanationService:
    """Verbalise ``SelectionDecision``; never change its verdict."""

    def __init__(self, provider: Any | None = None) -> None:
        self.provider = provider

    # ── Public API ────────────────────────────────────────────────────────
    def explain(self, decision: SelectionDecision) -> dict[str, Any]:
        """Return ``{"text", "source", "engine_eligible"}``.

        ``source`` is ``"composed"`` when the deterministic text is used
        (no provider, provider failure, or contradicting output) and
        ``"llm"`` for a grounded provider paraphrase.
        """
        composed = self.compose(decision)
        fallback = {
            "text": composed,
            "source": "composed",
            "engine_eligible": decision.eligible,
        }
        if self.provider is None:
            return fallback

        prompt = self._build_prompt(decision)
        try:
            llm_text = self.provider.chat(prompt)
        except Exception:  # noqa: BLE001 — provider failures must degrade
            return fallback
        if not isinstance(llm_text, str) or not llm_text.strip():
            return fallback
        if not self._validate_verdict(llm_text, decision.eligible):
            return fallback
        return {
            "text": llm_text.strip(),
            "source": "llm",
            "engine_eligible": decision.eligible,
        }

    # ── Deterministic composition ────────────────────────────────────────
    def compose(self, decision: SelectionDecision) -> str:
        course = f"«{decision.course_title}» (کد {_fa(decision.course_code)})"
        term = decision.term_name or "ترم جاری"
        totals = (
            f"واحدهای برنامه فعلی {_fa(decision.planned_credits)} + "
            f"این درس {_fa(decision.course_credits)} = "
            f"{_fa(decision.planned_credits + decision.course_credits)} از سقف "
            f"{_fa(decision.credit_limit)}"
        )
        if decision.eligible:
            return (
                f"نتیجه بررسی قواعد انتخاب واحد برای درس {course} در {term}: "
                f"شرایط لازم بر اساس سابقه قبولی، پیش‌نیازها، ارائه ترم جاری و "
                f"برنامه فعلی شما برآورده است ({totals})."
            )
        lines = []
        for reason in decision.reasons:
            lines.append(f"- {reason.message}")
        reasons_block = "\n".join(lines) if lines else "- دلیل مشخصی ثبت نشده است."
        return (
            f"نتیجه بررسی قواعد انتخاب واحد برای درس {course} در {term}: "
            f"انتخاب این درس در برنامه فعلی شما مجاز نیست ({totals}).\n"
            f"دلایل:\n{reasons_block}"
        )

    # ── LLM plumbing ─────────────────────────────────────────────────────
    def _build_prompt(self, decision: SelectionDecision) -> str:
        payload = json.dumps(decision.to_dict(), ensure_ascii=False)
        return (
            "این خروجی JSON از موتور قاعده‌محور انتخاب واحد سامانه است و تنها "
            "منبع معتبر برای پاسخ شما محسوب می‌شود.\n"
            "وظیفه شما فقط بازگویی (paraphrase) همین نتیجه است:\n"
            "- نتیجه نهایی (مجاز بودن یا نبودن) را بدون تغییر بگذارید.\n"
            "- فقط به دلایل ذکرشده اشاره کنید؛ ادعای جدیدی درباره ظرفیت، "
            "اساتید یا قواعد دیگر اضافه نکنید.\n"
            "- پاسخ فارسی و حداکثر سه جمله باشد.\n\n"
            f"ENGINE_RESULT:\n{payload}"
        )

    def _validate_verdict(self, text: str, eligible: bool) -> bool:
        """Reject any output whose verdict contradicts the engine."""
        haystack = normalize_persian(text)
        if not haystack:
            return False
        if eligible:
            # An eligible answer must not claim ineligibility in any form.
            for phrase in _PHRASES_INELIGIBLE:
                if _contains_phrase(haystack, phrase):
                    return False
            return True
        # An ineligible answer must not carry an *affirmed* eligibility
        # claim: negation prefixes are stripped first so «مجاز نیست» («not
        # allowed») and «نمی‌توانید» cannot be misread as eligibility.
        remainder = haystack
        for negation in _NEGATION_PREFIXES:
            remainder = remainder.replace(negation, " ")
        for phrase in _PHRASES_ELIGIBLE:
            if _contains_phrase(remainder, phrase):
                return False
        return True
