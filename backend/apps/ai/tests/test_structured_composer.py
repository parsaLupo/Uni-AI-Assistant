"""Deterministic answer composition for STRUCTURED mode.

The composer replaces the LLM for structured questions because the database
facts fully determine the answer; these tests pin the composed Persian text,
the fallback rule (unknown/incomplete facts → normal LLM path), the unchanged
HYBRID path, and the SSE payload contract (token + done) for composed answers.
"""

from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from apps.ai.answer import AnswerService
from apps.ai.modes import ExecutionMode
from apps.ai.providers import MockLLMProvider
from apps.ai.router import QuestionRouter
from apps.ai.structured_composer import compose_structured_answer
from apps.ai.tests.test_course_matching import CatalogFixtureMixin

PREREQUISITES_FACT = {
    "type": "prerequisites",
    "course_code": "1916013",
    "course_title": "سیستم های عامل",
    "prerequisites": [
        {"code": "1916006", "title": "ساختمانهای داده"},
        {"code": "1916012", "title": "معماری کامپیوتر"},
    ],
}


class ComposerTextTests(SimpleTestCase):
    """Pure text composition; no database needed."""

    def test_prerequisites_listed_from_fact(self):
        text = compose_structured_answer([PREREQUISITES_FACT])
        self.assertIn("پیش‌نیازهای «سیستم های عامل»", text)
        self.assertIn("ساختمانهای داده", text)
        self.assertIn("معماری کامپیوتر", text)
        # Codes using Persian digits for display
        self.assertIn("۱۹۱۶۰۰۶", text)
        self.assertIn("۱۹۱۶۰۱۲", text)

    def test_empty_prerequisites_message(self):
        fact = {**PREREQUISITES_FACT, "prerequisites": []}
        text = compose_structured_answer([fact])
        self.assertIn("پیش‌نیازی برای «سیستم های عامل»", text)
        self.assertIn("ثبت نشده", text)

    def test_course_ambiguous_clarification_lists_candidates(self):
        fact = {
            "type": "course_ambiguous",
            "matches": [
                {"code": "2001", "title": "پایگاه داده ها"},
                {"code": "2002", "title": "پایگاه داده ها"},
            ],
            "note": "چند درس مشابه پیدا شد.",
        }
        text = compose_structured_answer([fact])
        self.assertIn("چند درس مشابه پیدا شد.", text)
        self.assertIn("«پایگاه داده ها» (کد ۲۰۰۱)", text)
        self.assertIn("«پایگاه داده ها» (کد ۲۰۰۲)", text)

    def test_known_fact_types_compose(self):
        cases = [
            (
                {
                    "type": "credits",
                    "course_code": "1916001",
                    "course_title": "کارگاه کامپیوتر",
                    "credits": 1,
                },
                "۱ واحد",
            ),
            (
                {
                    "type": "exam",
                    "course_code": "1916013",
                    "course_title": "سیستم های عامل",
                    "term": "ترم اول",
                    "starts_at": "2027-01-05T09:00:00",
                    "ends_at": "2027-01-05T11:00:00",
                    "classroom": "کلاس ۲",
                },
                "برنامه امتحان",
            ),
            (
                {
                    "type": "eligibility",
                    "course_code": "1916013",
                    "course_title": "سیستم های عامل",
                    "eligible": False,
                    "missing_prerequisites": ["1916006"],
                },
                "۱۹۱۶۰۰۶",
            ),
            (
                {
                    "type": "eligibility",
                    "course_code": "1916013",
                    "course_title": "سیستم های عامل",
                    "eligible": True,
                    "missing_prerequisites": [],
                },
                "مجاز",
            ),
            (
                {
                    "type": "academic_calendar",
                    "term_name": "نیمسال اول",
                    "academic_year": "1405-1406",
                    "starts_at": "2026-09-01",
                    "ends_at": "2027-01-09",
                },
                "نیمسال اول",
            ),
        ]
        for fact, expected in cases:
            with self.subTest(type=fact["type"]):
                text = compose_structured_answer([fact])
                self.assertIn(expected, text)
                # No composed text may contain ASCII digits
                for digit in "0123456789":
                    self.assertNotIn(digit, text)

    def test_unknown_fact_type_falls_back_to_none(self):
        self.assertIsNone(compose_structured_answer([{"type": "mystery", "x": 1}]))

    def test_incomplete_fact_falls_back_to_none(self):
        fact = {"type": "prerequisites"}  # no course_code/course_title
        self.assertIsNone(compose_structured_answer([fact]))

    def test_empty_facts_fall_back_to_none(self):
        self.assertIsNone(compose_structured_answer([]))
        self.assertIsNone(compose_structured_answer(None))


class _FakeStructured:
    def __init__(self, facts: list[dict]) -> None:
        self.facts = facts
        self.calls: list[str] = []

    def answer(self, question, user=None):
        self.calls.append(question)
        return {"facts": self.facts, "term": None}


class _FakeRetrieval:
    def retrieve(self, question, filters=None):
        return []


class ComposerWiringTests(TestCase):
    def _service(self, facts, **kwargs):
        provider = kwargs.pop(
            "provider", MockLLMProvider(response_text="پاسخ مدل زبانی")
        )
        structured = _FakeStructured(facts)
        kwargs.setdefault("router", QuestionRouter())
        return provider, AnswerService(
            provider=provider,
            structured_service=structured,
            **kwargs,
        )

    def test_answer_composes_structured_facts_without_provider(self):
        provider, service = self._service([PREREQUISITES_FACT])
        result = service.answer("پیش نیاز درس سیستم عامل چیست؟")
        self.assertEqual(result["mode"], ExecutionMode.STRUCTURED.value)
        self.assertFalse(result["insufficient_evidence"])
        self.assertEqual(provider.call_count, 0)
        self.assertNotIn("پاسخ مدل زبانی", result["answer"])
        self.assertIn("ساختمانهای داده", result["answer"])
        self.assertIn("معماری کامپیوتر", result["answer"])
        self.assertEqual(result["structured_evidence"][0]["course_code"], "1916013")

    def test_unknown_fact_type_falls_back_to_llm(self):
        provider, service = self._service([{"type": "mystery", "x": 1}])
        result = service.answer("پیش نیاز درس سیستم عامل چیست؟")
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(result["answer"], "پاسخ مدل زبانی")

    def test_incomplete_fact_falls_back_to_llm(self):
        provider, service = self._service([{"type": "prerequisites"}])
        result = service.answer("پیش نیاز درس سیستم عامل چیست؟")
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(result["answer"], "پاسخ مدل زبانی")

    def test_hybrid_mode_still_uses_provider(self):
        provider = MockLLMProvider(response_text="پاسخ [1] هیبریدی")
        structured = _FakeStructured([PREREQUISITES_FACT])
        service = AnswerService(
            provider=provider,
            router=QuestionRouter(),
            structured_service=structured,
            retrieval_service=_FakeRetrieval(),
        )
        result = service.answer(
            "با توجه به آیین‌نامه و دروس پاس‌شده من چه درس‌هایی را می‌توانم بردارم؟"
        )
        self.assertEqual(result["mode"], ExecutionMode.HYBRID.value)
        self.assertEqual(provider.call_count, 1)
        self.assertIn("هیبریدی", result["answer"])

    def test_stream_yields_composed_token_and_matching_done(self):
        provider, service = self._service([PREREQUISITES_FACT])
        events = list(service.answer_stream("پیش نیاز درس سیستم عامل چیست؟"))
        self.assertEqual(events[0]["event"], "token")
        token_text = events[0]["data"]["text"]
        self.assertEqual(events[-1]["event"], "done")
        done = events[-1]["data"]
        self.assertEqual(done["answer"], token_text)
        self.assertEqual(done["mode"], ExecutionMode.STRUCTURED.value)
        self.assertFalse(done["insufficient_evidence"])
        self.assertEqual(done["structured_evidence"][0]["course_code"], "1916013")
        self.assertIn("ساختمانهای داده", token_text)
        self.assertEqual(provider.call_count, 0)

    def test_stream_falls_back_to_llm_for_unknown_fact_type(self):
        provider, service = self._service([{"type": "mystery", "x": 1}])
        events = list(service.answer_stream("پیش نیاز درس سیستم عامل چیست؟"))
        self.assertEqual(provider.call_count, 1)
        done = events[-1]["data"]
        self.assertEqual(done["answer"], "پاسخ مدل زبانی")


class ComposerEndToEndTests(CatalogFixtureMixin, TestCase):
    """Real StructuredQueryService + resolver against the seeded fixture."""

    def test_operating_systems_prerequisites_answered_deterministically(self):
        provider = MockLLMProvider(response_text="پاسخ مدل")
        service = AnswerService(
            provider=provider,
            router=QuestionRouter(),  # keyword rules only; provider counts answers
            structured_service=self.service,
        )
        result = service.answer("پیش نیاز درس سیستم عامل چیست؟")
        self.assertEqual(result["mode"], ExecutionMode.STRUCTURED.value)
        self.assertFalse(result["insufficient_evidence"])
        self.assertEqual(provider.call_count, 0)
        self.assertIn("ساختمانهای داده", result["answer"])
        self.assertIn("معماری کامپیوتر", result["answer"])

    def test_stream_end_to_end_composed(self):
        provider = MockLLMProvider(response_text="پاسخ مدل")
        service = AnswerService(
            provider=provider,
            router=QuestionRouter(),
            structured_service=self.service,
        )
        events = list(service.answer_stream("پیش نیاز درس سیستم عامل چیست؟"))
        token_text = events[0]["data"]["text"]
        self.assertIn("معماری کامپیوتر", token_text)
        self.assertEqual(events[-1]["data"]["answer"], token_text)
        self.assertEqual(provider.call_count, 0)
