"""Phase 11 — explanation-layer tests: composition + the no-override rule.

The acceptance criterion under test: *AI explanation does not override backend
eligibility*. A provider that contradicts the engine verdict — or one that
fails, returns empties, or invents extra eligibility conditions — must never
reach the user; the deterministic composed text replaces it.
"""

from __future__ import annotations

from apps.ai.providers import MockLLMProvider
from apps.ai.selection_explanation import SelectionExplanationService
from apps.students.course_selection import (
    CREDIT_LIMIT_EXCEEDED,
    PREREQUISITE_MISSING,
    SelectionDecision,
    SelectionReason,
)


def eligible_decision() -> SelectionDecision:
    return SelectionDecision(
        course_code="1916014",
        course_title="آمار و احتمال",
        course_credits=3,
        eligible=True,
        reasons=[],
        term_name="نیمسال اول ۱۴۰۵-۱۴۰۶",
        passed_course_codes=["1916002"],
        missing_prerequisite_codes=[],
        planned_course_codes=["1916009"],
        planned_credits=6,
        extra_course_codes=[],
        extra_credits=0,
        credit_limit=20,
    )


def ineligible_decision() -> SelectionDecision:
    missing = SelectionReason(
        code=PREREQUISITE_MISSING,
        message=(
            "ابتدا باید این پیش‌نیازها را با موفقیت بگذرانید: "
            "1916002"
        ),
        params={"codes": ["1916002"], "count": 1},
    )
    credits = SelectionReason(
        code=CREDIT_LIMIT_EXCEEDED,
        message="جمع واحدهای ترم (23) از سقف مجاز (20) بیشتر است.",
        params={"limit": 20, "planned": 19, "candidate": 3, "extra": 1, "total": 23},
    )
    return SelectionDecision(
        course_code="1916014",
        course_title="آمار و احتمال",
        course_credits=3,
        eligible=False,
        reasons=[missing, credits],
        term_name="نیمسال اول ۱۴۰۵-۱۴۰۶",
        passed_course_codes=[],
        missing_prerequisite_codes=["1916002"],
        planned_course_codes=["1916011"],
        planned_credits=19,
        extra_course_codes=["1916001"],
        extra_credits=1,
        credit_limit=20,
    )


class RecordingProvider:
    """MockLLMProvider variant that remembers the prompt it was given."""

    provider_name = "recording"

    def __init__(self, response_text: str | None = None) -> None:
        self.model_id = "recording"
        self.last_prompt: str | None = None
        self.response_text = response_text

    def chat(self, prompt: str, **_kwargs) -> str:
        self.last_prompt = prompt
        return self.response_text or ""


# ── Deterministic composition (no provider) ────────────────────────────────


def test_eligible_composed_without_any_provider():
    result = SelectionExplanationService().explain(eligible_decision())
    assert result["source"] == "composed"
    assert result["engine_eligible"] is True
    assert "آمار و احتمال" in result["text"]
    assert "1916014" in result["text"] or "۱۹۱۶۰۱۴" in result["text"]


def test_ineligible_composed_lists_every_reason_message():
    service = SelectionExplanationService()
    result = service.compose(ineligible_decision())
    assert "مجاز نیست" in result
    assert "پیش‌نیازها" in result and "1916002" in result
    assert "۲۰" in result  # credit limit rendered with Persian digits


def test_credit_totals_rendered_in_composed_text():
    text = SelectionExplanationService().compose(ineligible_decision())
    assert "۲۲" in text  # planned 19 + candidate 3
    assert "۲۰" in text  # limit
    assert "۲" in text  # extra credit rendered in Persian digits


# ── Prompt is engine-JSON only ─────────────────────────────────────────────


def test_prompt_carries_only_the_engine_json():
    provider = RecordingProvider(response_text="x")
    decision = ineligible_decision()
    service = SelectionExplanationService(provider)
    service.explain(decision)
    prompt = provider.last_prompt
    assert prompt is not None
    assert "ENGINE_RESULT" in prompt
    # The verdict travels inside the JSON — and as an instruction, never as a
    # question that invites the model to decide by itself.
    assert '"eligible": false' in prompt
    assert "تغییر" in prompt  # "never change the verdict" rule


# ── Grounded LLM paraphrase passes through when consistent ────────────────


def test_consistent_llm_paraphrase_for_eligible_is_accepted():
    provider = MockLLMProvider(
        response_text="طبق نتیجه موتور قواعد سامانه، درس «آمار و احتمال» برای شما قابل برداشتن است."
    )
    result = SelectionExplanationService(provider).explain(eligible_decision())
    assert result["source"] == "llm"
    assert result["engine_eligible"] is True
    assert "قابل برداشتن" in result["text"]


def test_consistent_llm_paraphrase_with_negated_eligible_word_is_accepted():
    provider = MockLLMProvider(
        response_text="نگاه به نتیجه موتور: انتخاب این درس مجاز نیست و باید ابتدا پیش‌نیاز 1916002 را بگذرانید."
    )
    result = SelectionExplanationService(provider).explain(ineligible_decision())
    assert result["source"] == "llm"
    assert result["engine_eligible"] is False
    assert "مجاز نیست" in result["text"]


# ── Contradiction → deterministic fallback (the acceptance criterion) ─────


def test_contradicting_llm_cannot_make_ineligible_course_eligible():
    provider = MockLLMProvider(
        response_text="بله! این درس برای شما مجاز است و می‌توانید آن را بردارید."
    )
    service = SelectionExplanationService(provider)
    result = service.explain(ineligible_decision())

    composed = service.compose(ineligible_decision())
    assert result["source"] == "composed"
    assert result["engine_eligible"] is False
    assert result["text"] == composed
    assert "مجاز است" not in result["text"]


def test_contradicting_llm_cannot_make_eligible_course_ineligible():
    provider = MockLLMProvider(
        response_text="متأسفانه این درس برای شما مجاز نیست."
    )
    result = SelectionExplanationService(provider).explain(eligible_decision())
    assert result["source"] == "composed"
    assert result["engine_eligible"] is True
    assert "مجاز نیست" not in result["text"]


def test_negated_eligibility_claim_is_caught_even_with_zwnj_variants():
    provider = MockLLMProvider(
        response_text="این درس مجاز‌نیست."  # ZWNJ fused form
    )
    result = SelectionExplanationService(provider).explain(eligible_decision())
    assert result["source"] == "composed"
    assert result["engine_eligible"] is True


# ── Provider failure / malformed output → composed fallback ───────────────


def test_provider_exception_falls_back_to_composed():
    provider = MockLLMProvider(fail_with=TimeoutError("boom"))
    result = SelectionExplanationService(provider).explain(eligible_decision())
    assert result["source"] == "composed"
    assert result["engine_eligible"] is True


def test_empty_llm_output_falls_back_to_composed():
    provider = MockLLMProvider(malformed=True)  # returns whitespace only
    result = SelectionExplanationService(provider).explain(eligible_decision())
    assert result["source"] == "composed"


def test_non_string_output_falls_back_to_composed():
    class WeirdProvider:
        provider_name = "weird"

        def chat(self, prompt, **_kwargs):  # noqa: ARG002
            return None  # broken adapter

    result = SelectionExplanationService(WeirdProvider()).explain(eligible_decision())
    assert result["source"] == "composed"
    assert result["engine_eligible"] is True


# ── Serialisation round-trip (explanation layer input contract) ───────────


def test_decision_dict_round_trip_is_lossless():
    decision = ineligible_decision()
    rebuilt = SelectionDecision.from_dict(decision.to_dict())
    assert rebuilt.to_dict() == decision.to_dict()
