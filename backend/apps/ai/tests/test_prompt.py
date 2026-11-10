"""PromptService source-content truncation (provider body-size guard).

The LLM provider rejects large request bodies with HTTP 413; document chunks
are big enough that five retrieved sources can exceed it. The prompt builder
therefore truncates each source's supplied (untrusted) content instead of
failing the whole answer.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.ai.prompt import PromptService


class SourceContentTruncationTests(SimpleTestCase):
    def _source(self, content: str) -> dict:
        return {
            "document_id": 1,
            "label": "آیین‌نامه",
            "page_number": 3,
            "section_title": "شرایط ثبت‌نام",
            "score": 0.9,
            "content": content,
        }

    def test_truncated_entry_marks_the_cut(self):
        service = PromptService()
        long_content = "الف" * 5000
        prompt = service.build(question="س", mode="rag", sources=[self._source(long_content)])
        self.assertIn("[ادامه متن کامل در سند اصلی]", prompt)
        self.assertNotIn("ا" * (service.SOURCE_CONTENT_MAX_CHARS + 10), prompt)

    def test_short_content_kept_intact(self):
        service = PromptService()
        short = "شرایط مشروطی در آیین‌نامه آمده است."
        prompt = service.build(question="س", mode="rag", sources=[self._source(short)])
        self.assertIn(short, prompt)

    def test_five_large_stay_sources_under_size_budget(self):
        """Realistic worst case: 5 full chunks fit under ~20 KB."""
        service = PromptService()
        sources = [self._source("متنی " * 900) for _ in range(5)]  # ~4500 chars each
        prompt = service.build(question="س", mode="rag", sources=sources)
        self.assertLess(len(prompt.encode("utf-8")), 20000)
        # Every source stays referenced despite truncation
        for index in range(1, 6):
            self.assertIn(f"[{index}]", prompt)

    def test_missing_content_does_not_break_build(self):
        service = PromptService()
        source = self._source("")
        source.pop("content")
        prompt = service.build(question="س", mode="rag", sources=[source])
        self.assertIn("UNTRUSTED DATA", prompt)
