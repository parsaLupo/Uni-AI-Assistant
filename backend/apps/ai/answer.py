"""Grounded answer service for Phase 09."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

from apps.ai.citations import CitationService
from apps.ai.formatter import INSUFFICIENT_EVIDENCE_MESSAGE, AnswerFormatter
from apps.ai.modes import ExecutionMode
from apps.ai.prompt import PromptService
from apps.ai.providers import LLMProvider
from apps.ai.router import QuestionRouter
from apps.ai.structured import StructuredQueryService
from apps.ai.structured_composer import compose_structured_answer
from apps.common.errors import (
    AI_PROVIDER_ERROR,
    RETRIEVAL_ERROR,
    VALIDATION_ERROR,
    ApiError,
)
from apps.rag.retrieval import RetrievalService

logger = logging.getLogger("app.ai.answer")


class EvidenceSet:
    """Tracks evidence from a single retrieval path with sufficiency metadata."""

    def __init__(self, items: list[dict[str, Any]], source_type: str) -> None:
        self.items = items or []
        self.source_type = source_type  # "structured" or "document"
        self.sufficient = len(self.items) > 0
        self.count = len(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "count": self.count,
            "sufficient": self.sufficient,
            "items": self.items,
        }


class AnswerService:
    def __init__(
        self,
        provider: LLMProvider | None = None,
        *,
        router: QuestionRouter | None = None,
        structured_service: StructuredQueryService | None = None,
        retrieval_service: RetrievalService | None = None,
        prompt_service: PromptService | None = None,
        formatter: AnswerFormatter | None = None,
        citation_service: CitationService | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.provider = provider
        self.router = router or QuestionRouter(provider)
        self.structured_service = structured_service or StructuredQueryService()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.prompt_service = prompt_service or PromptService()
        self.formatter = formatter or AnswerFormatter()
        self.citation_service = citation_service or CitationService()
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = int(max_retries)
        self._last_provider_latency_ms: int | None = None

    def _evaluate_evidence_sufficiency(
        self,
        mode: ExecutionMode,
        structured_evidence: EvidenceSet,
        document_evidence: EvidenceSet,
    ) -> bool:
        """Determine if evidence is sufficient to answer the question."""
        if mode == ExecutionMode.STRUCTURED:
            return structured_evidence.sufficient
        if mode == ExecutionMode.RAG:
            return document_evidence.sufficient
        if mode == ExecutionMode.HYBRID:
            if structured_evidence.sufficient and document_evidence.sufficient:
                return True
            if structured_evidence.sufficient and not document_evidence.sufficient:
                return True
            if document_evidence.sufficient and not structured_evidence.sufficient:
                return True
            return False
        return True

    def _detect_conflicts(
        self,
        structured_evidence: EvidenceSet,
        document_evidence: EvidenceSet,
    ) -> list[dict[str, Any]]:
        """Detect conflicts between structured and document evidence."""
        conflicts: list[dict[str, Any]] = []
        structured_topics = {item.get("type", "") for item in structured_evidence.items}
        document_topics = set()
        for item in document_evidence.items:
            content = item.get("content", "").lower()
            if "پیش‌نیاز" in content or "پیش نیاز" in content:
                document_topics.add("prerequisites")
            if "امتحان" in content:
                document_topics.add("exams")
            if "ثبت‌نام" in content:
                document_topics.add("registration")
        overlap = structured_topics & document_topics
        if overlap:
            conflicts.append(
                {
                    "topic": sorted(overlap),
                    "description": (
                        "ساختار داده‌های پایگاه و اسناد بازیابی شده ممکن است "
                        "اطلاعات متضاربة داشته باشند."
                    ),
                    "structured_count": structured_evidence.count,
                    "document_count": document_evidence.count,
                }
            )
        return conflicts

    def answer(
        self,
        question: str,
        *,
        user=None,
        retrieval_filters: dict[str, Any] | None = None,
        message_id: int | None = None,
        assistant_message_id: int | None = None,
        message=None,
    ) -> dict[str, Any]:
        if not (question or "").strip():
            raise ApiError(VALIDATION_ERROR, "پرسش نمی‌تواند خالی باشد.", http_status=400)

        started = time.monotonic()
        mode = self.router.classify(question)

        target_message_id = message_id
        if target_message_id is None:
            target_message_id = assistant_message_id
        if target_message_id is None and message is not None:
            target_message_id = getattr(message, "pk", message)
        self._persist_routing_mode(target_message_id, mode)

        structured_evidence = EvidenceSet([], "structured")
        document_evidence = EvidenceSet([], "document")

        if mode in {ExecutionMode.STRUCTURED, ExecutionMode.HYBRID}:
            try:
                structured_result = self.structured_service.answer(question, user=user)
                structured_evidence = EvidenceSet(
                    list(structured_result.get("facts", [])), "structured"
                )
            except Exception as exc:
                logger.exception("structured_query_failed")
                raise ApiError(
                    RETRIEVAL_ERROR, "پاسخ ساختاریابی‌شده قابل تولید نیست.", http_status=503
                ) from exc

        if mode in {ExecutionMode.RAG, ExecutionMode.HYBRID}:
            try:
                raw_sources = self.retrieval_service.retrieve(
                    question, filters=retrieval_filters
                )
                document_evidence = EvidenceSet(raw_sources, "document")
            except Exception as exc:
                logger.exception("rag_retrieval_failed")
                raise ApiError(
                    RETRIEVAL_ERROR, "بازیابی اسناد قابل تولید نیست.", http_status=503
                ) from exc

        insufficient = not self._evaluate_evidence_sufficiency(
            mode, structured_evidence, document_evidence
        )
        conflicts = self._detect_conflicts(structured_evidence, document_evidence)

        if mode == ExecutionMode.OUT_OF_SCOPE:
            answer_text = (
                "این پرسش خارج از دامنه پشتیبانی‌شده دانشگاه است. "
                "لطفاً سوالی درباره دروس، امتحانات، اساتید، تقویم یا مقررات دانشگاهی بپرسید."
            )
            raw_output = answer_text
            insufficient = True
        elif insufficient:
            answer_text = INSUFFICIENT_EVIDENCE_MESSAGE
            raw_output = answer_text
        else:
            # STRUCTURED questions are answered directly from the database
            # facts: the facts fully determine the answer, and routing them
            # through a chat LLM adds a failure point (refusals, provider
            # outages) without adding information. HYBRID keeps the LLM path
            # because it must blend facts with retrieved document text.
            composed: str | None = None
            if mode == ExecutionMode.STRUCTURED:
                composed = compose_structured_answer(structured_evidence.items)

            if composed is not None:
                logger.info(
                    "answer_composed_from_structured_facts facts=%s",
                    structured_evidence.count,
                )
                answer_text = self.citation_service.validate(
                    composed, document_evidence.items
                )
                raw_output = answer_text
            else:
                prompt = self.prompt_service.build(
                    question=question,
                    mode=mode.value,
                    structured_facts=structured_evidence.items,
                    sources=document_evidence.items,
                )

                if self.provider is None:
                    raise ApiError(
                        AI_PROVIDER_ERROR,
                        "سرویس پرونده‌سازی پاسخ در دسترس نیست.",
                        http_status=503,
                    )

                try:
                    raw = self.provider.chat(
                        prompt, timeout=self.timeout_seconds, max_retries=self.max_retries
                    )
                except Exception as exc:
                    logger.warning(
                        "llm_provider_failed category=%s", getattr(exc, "category", "unknown")
                    )
                    logger.exception("llm_provider_failed")
                    raise ApiError(
                        AI_PROVIDER_ERROR,
                        "سرویس هوش مصنوعی موقتاً در دسترس نیست.",
                        http_status=503,
                    ) from exc

                raw_output = (raw or "").strip()
                if not raw_output:
                    raise ApiError(
                        AI_PROVIDER_ERROR, "خروجی مدل نامعتبر است.", http_status=503
                    )

                answer_text = self.formatter.format(
                    raw_output, document_evidence.items, insufficient=False
                )
                answer_text = self.citation_service.validate(
                    answer_text, document_evidence.items
                )
        formatted_structured = [
            {
                "source_type": "structured",
                "type": item.get("type"),
                "course_code": item.get("course_code"),
                "course_title": item.get("course_title"),
                "facts": item,
            }
            for item in structured_evidence.items
        ]

        formatted_sources = [
            {
                "source_type": "document",
                # chunk_id is what the conversation layer keys MessageSource
                # rows on (Phase 10); dropping it silently emptied the
                # per-message citation list the UI renders (found by Phase 14
                # critical-journey 5).
                "chunk_id": source.get("chunk_id"),
                "document_id": source.get("document_id"),
                "label": source.get("label"),
                "page": source.get("page_number"),
                "section": source.get("section_title"),
                "relevance_score": round(float(source.get("score", 0.0)), 4),
            }
            for source in document_evidence.items
        ]

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "answer_complete mode=%s structured_count=%s document_count=%s "
            "insufficient=%s duration_ms=%s model=%s",
            mode.value,
            structured_evidence.count,
            document_evidence.count,
            insufficient,
            duration_ms,
            getattr(self.provider, "model_id", "none"),
        )

        result: dict[str, Any] = {
            "mode": mode.value,
            "answer": answer_text,
            "sources": formatted_sources,
            "structured_evidence": formatted_structured,
            "document_evidence": [
                {
                    "source_type": "document",
                    **{
                        k: v
                        for k, v in source.items()
                        if k
                        in (
                            "document_id",
                            "label",
                            "page_number",
                            "section_title",
                            "content",
                            "score",
                        )
                    },
                }
                for source in document_evidence.items
            ],
            "insufficient_evidence": bool(insufficient),
            "evidence_conflicts": conflicts,
            "provider": {
                "name": getattr(self.provider, "provider_name", "none"),
                "model_id": getattr(self.provider, "model_id", None),
            },
            "latency_ms": duration_ms,
        }

        if message_id is None:
            return result

        try:
            from apps.conversations.models import Message
        except Exception:
            logger.warning("routing_mode_persistence_unavailable")
            return result
        try:
            Message.objects.filter(pk=message_id).update(retrieval_mode=mode.value)
        except Exception:
            logger.exception("routing_mode_persistence_failed")

        return result
    def answer_stream(
        self,
        question: str,
        *,
        user=None,
        retrieval_filters: dict[str, Any] | None = None,
        message_id: int | None = None,
        assistant_message_id: int | None = None,
        message=None,
    ) -> Iterator[dict[str, Any]]:
        if not (question or "").strip():
            raise ApiError(VALIDATION_ERROR, "پرسش نمی‌تواند خالی باشد.", http_status=400)

        started = time.monotonic()
        mode = self.router.classify(question)

        target_message_id = message_id
        if target_message_id is None:
            target_message_id = assistant_message_id
        if target_message_id is None and message is not None:
            target_message_id = getattr(message, "pk", message)
        self._persist_routing_mode(target_message_id, mode)

        structured_evidence = EvidenceSet([], "structured")
        document_evidence = EvidenceSet([], "document")

        if mode in {ExecutionMode.STRUCTURED, ExecutionMode.HYBRID}:
            try:
                structured_result = self.structured_service.answer(question, user=user)
                structured_evidence = EvidenceSet(
                    list(structured_result.get("facts", [])), "structured"
                )
            except Exception as exc:
                logger.exception("structured_query_failed_stream")
                raise ApiError(
                    RETRIEVAL_ERROR,
                    "پاسخ ساختاریابی‌شده قابل تولید نیست.",
                    http_status=503,
                ) from exc

        if mode in {ExecutionMode.RAG, ExecutionMode.HYBRID}:
            try:
                raw_sources = self.retrieval_service.retrieve(
                    question, filters=retrieval_filters
                )
                document_evidence = EvidenceSet(raw_sources, "document")
            except Exception as exc:
                logger.exception("rag_retrieval_failed_stream")
                raise ApiError(
                    RETRIEVAL_ERROR,
                    "بازیابی اسناد قابل تولید نیست.",
                    http_status=503,
                ) from exc

        insufficient = not self._evaluate_evidence_sufficiency(
            mode, structured_evidence, document_evidence
        )
        conflicts = self._detect_conflicts(structured_evidence, document_evidence)

        if mode == ExecutionMode.OUT_OF_SCOPE:
            out_of_scope_text = (
                "این پرسش خارج از دامنه پشتیبانی‌شده دانشگاه است. "
                "لطفاً سوالی درباره دروس، امتحانات، اساتید، تقویم یا مقررات دانشگاهی بپرسید."
            )
            yield {"event": "token", "data": {"text": out_of_scope_text}}
            yield {
                "event": "done",
                "data": {
                    "mode": mode.value,
                    "answer": out_of_scope_text,
                    "sources": [],
                    "structured_evidence": [],
                    "document_evidence": [],
                    "insufficient_evidence": True,
                    "evidence_conflicts": [],
                    "provider": {
                        "name": getattr(self.provider, "provider_name", "none"),
                        "model_id": getattr(self.provider, "model_id", None),
                    },
                    "latency_ms": int((time.monotonic() - started) * 1000),
                },
            }
            self._persist_routing_mode(target_message_id, mode)
            return
        elif insufficient:
            yield {"event": "token", "data": {"text": INSUFFICIENT_EVIDENCE_MESSAGE}}
            yield {
                "event": "done",
                "data": {
                    "mode": mode.value,
                    "answer": INSUFFICIENT_EVIDENCE_MESSAGE,
                    "sources": [],
                    "structured_evidence": [],
                    "document_evidence": [],
                    "insufficient_evidence": True,
                    "evidence_conflicts": conflicts,
                    "provider": {
                        "name": getattr(self.provider, "provider_name", "none"),
                        "model_id": getattr(self.provider, "model_id", None),
                    },
                    "latency_ms": int((time.monotonic() - started) * 1000),
                },
            }
            self._persist_routing_mode(target_message_id, mode)
            return

        # Evidence formatting is identical for both answer paths below.
        formatted_structured = [
            {
                "source_type": "structured",
                "type": item.get("type"),
                "course_code": item.get("course_code"),
                "course_title": item.get("course_title"),
                "facts": item,
            }
            for item in structured_evidence.items
        ]

        formatted_sources = [
            {
                "source_type": "document",
                # chunk_id is what the conversation layer keys MessageSource
                # rows on (Phase 10); dropping it silently emptied the
                # per-message citation list the UI renders (found by Phase 14
                # critical-journey 5).
                "chunk_id": source.get("chunk_id"),
                "document_id": source.get("document_id"),
                "label": source.get("label"),
                "page": source.get("page_number"),
                "section": source.get("section_title"),
                "relevance_score": round(float(source.get("score", 0.0)), 4),
            }
            for source in document_evidence.items
        ]

        # STRUCTURED questions are answered directly from the database facts
        # (same rationale as in answer()); HYBRID keeps the LLM path.
        composed: str | None = None
        if mode == ExecutionMode.STRUCTURED:
            composed = compose_structured_answer(structured_evidence.items)

        if composed is not None:
            logger.info(
                "answer_composed_from_structured_facts facts=%s",
                structured_evidence.count,
            )
            answer_text = self.citation_service.validate(
                composed, document_evidence.items
            )
            yield {"event": "token", "data": {"text": answer_text}}
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "answer_stream_complete mode=%s structured_count=%s document_count=%s "
                "insufficient=%s duration_ms=%s model=%s",
                mode.value,
                structured_evidence.count,
                document_evidence.count,
                False,
                duration_ms,
                getattr(self.provider, "model_id", "none"),
            )
            yield {
                "event": "done",
                "data": {
                    "mode": mode.value,
                    "answer": answer_text,
                    "sources": formatted_sources,
                    "structured_evidence": formatted_structured,
                    "document_evidence": document_evidence.items,
                    "insufficient_evidence": False,
                    "evidence_conflicts": conflicts,
                    "provider": {
                        "name": getattr(self.provider, "provider_name", "none"),
                        "model_id": getattr(self.provider, "model_id", None),
                    },
                    "latency_ms": duration_ms,
                },
            }
            self._persist_routing_mode(target_message_id, mode)
            return

        prompt = self.prompt_service.build(
            question=question,
            mode=mode.value,
            structured_facts=structured_evidence.items,
            sources=document_evidence.items,
        )

        accumulated = ""
        try:
            stream = getattr(self.provider, "chat_stream", None)
            if stream is not None:
                for chunk in stream(
                    prompt, timeout=self.timeout_seconds, max_retries=self.max_retries
                ):
                    if chunk:
                        accumulated += chunk
                        yield {"event": "token", "data": {"text": chunk}}
            else:
                raw = self.provider.chat(
                    prompt, timeout=self.timeout_seconds, max_retries=self.max_retries
                )
                accumulated = raw or ""
                if accumulated.strip():
                    yield {"event": "token", "data": {"text": accumulated.strip()}}
        except Exception as exc:
            logger.warning(
                "llm_provider_failed category=%s", getattr(exc, "category", "unknown")
            )
            logger.exception("llm_provider_failed")
            raise ApiError(
                AI_PROVIDER_ERROR,
                "سرویس هوش مصنوعی موقتاً در دسترس نیست.",
                http_status=503,
            ) from exc

        raw_output = accumulated.strip()
        if not raw_output:
            raise ApiError(
                AI_PROVIDER_ERROR, "خروجی مدل نامعتبر است.", http_status=503
            )
        answer_text = self.formatter.format(
            raw_output, document_evidence.items, insufficient=False
        )
        answer_text = self.citation_service.validate(answer_text, document_evidence.items)

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "answer_stream_complete mode=%s structured_count=%s document_count=%s "
            "insufficient=%s duration_ms=%s model=%s",
            mode.value,
            structured_evidence.count,
            document_evidence.count,
            insufficient,
            duration_ms,
            getattr(self.provider, "model_id", "none"),
        )

        yield {
            "event": "done",
            "data": {
                "mode": mode.value,
                "answer": answer_text,
                "sources": formatted_sources,
                "structured_evidence": formatted_structured,
                "document_evidence": document_evidence.items,
                "insufficient_evidence": False,
                "evidence_conflicts": conflicts,
                "provider": {
                    "name": getattr(self.provider, "provider_name", "none"),
                    "model_id": getattr(self.provider, "model_id", None),
                },
                "latency_ms": duration_ms,
            },
        }
        if message_id is None:
            return
        try:
            from apps.conversations.models import Message
        except Exception:
            logger.warning("routing_mode_persistence_unavailable_stream")
            return
        try:
            Message.objects.filter(pk=message_id).update(retrieval_mode=mode.value)
        except Exception:
            logger.exception("routing_mode_persistence_failed_stream")

    def _persist_routing_mode(self, message_id: Any, mode: ExecutionMode) -> None:
        if message_id is None:
            return
        try:
            from apps.conversations.models import Message
        except Exception:  # noqa: BLE001
            logger.warning("routing_mode_persistence_unavailable")
            return
        try:
            Message.objects.filter(pk=message_id).update(retrieval_mode=mode.value)
        except Exception:  # noqa: BLE001
            logger.exception("routing_mode_persistence_failed")

