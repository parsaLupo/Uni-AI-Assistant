"""Conversation endpoints (Phase 10)."""

from __future__ import annotations

import time

from apps.ai.answer import AnswerService
from apps.ai.providers import build_llm_provider_from_env
from apps.analytics.services import record_ai_request
from apps.common.errors import VALIDATION_ERROR, ApiError
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.pagination import StandardResultsSetPagination
from apps.conversations.models import Conversation, Message, MessageSource
from apps.conversations.serializers import (
    ConversationCreateSerializer,
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
)
from django.utils import timezone as dj_timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class ConversationViewSet(ConflictOnIntegrityMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Conversation.objects.filter(user=self.request.user)
        if self.action in {"list", "retrieve"}:
            qs = qs.filter(archived_at__isnull=True)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ConversationCreateSerializer
        if self.action in {"update", "partial_update"}:
            return ConversationCreateSerializer
        if self.action == "retrieve":
            return ConversationDetailSerializer
        return ConversationListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.archived_at = dj_timezone.now()
        instance.save(update_fields=["archived_at", "updated_at"])

    @action(detail=True, methods=["get"], url_path="messages")
    def messages(self, request, pk=None):
        conversation = self.get_object()
        qs = conversation.messages.order_by("created_at", "pk")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = MessageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="messages")
    def create_message(self, request, pk=None):
        conversation = self.get_object()

        content = (request.data.get("content") or "").strip()
        if not content:
            raise ApiError(VALIDATION_ERROR, "پرسش نمی‌تواند خالی باشد.", http_status=400)

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=content,
        )

        started = time.monotonic()
        try:
            result = AnswerService(provider=build_llm_provider_from_env()).answer(
                content, user=request.user
            )
        except ApiError as exc:
            # Phase 13 telemetry: one row per attempt, no message content.
            record_ai_request(
                user=request.user,
                outcome=exc.code,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            raise
        record_ai_request(
            user=request.user,
            mode=result.get("mode") or "",
            outcome="OK",
            latency_ms=result.get("latency_ms"),
        )
        duration_ms = int((time.monotonic() - started) * 1000)

        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=result["answer"],
            retrieval_mode=result.get("mode", ""),
            insufficient_evidence=bool(result.get("insufficient_evidence", False)),
            latency_ms=duration_ms,
        )

        for source in result.get("sources", []) or []:
            chunk_id = source.get("chunk_id")
            if chunk_id is None:
                continue
            try:
                MessageSource.objects.create(
                    message=assistant_message,
                    document_chunk_id=chunk_id,
                    source_label=source.get("label") or "",
                    relevance_score=float(source.get("relevance_score", 0.0) or 0.0),
                    citation_text="",
                )
            except Exception:  # noqa: BLE001
                continue

        if not conversation.title:
            conversation.title = content[:120]
        conversation.save(update_fields=["title", "updated_at"])

        return Response(
            {
                "message": MessageSerializer(assistant_message).data,
                "sources": result.get("sources", []),
                "structured_evidence": result.get("structured_evidence", []),
                "document_evidence": result.get("document_evidence", []),
                "evidence_conflicts": result.get("evidence_conflicts", []),
                "insufficient_evidence": bool(result.get("insufficient_evidence", False)),
                "user_message": MessageSerializer(user_message).data,
            },
            status=status.HTTP_201_CREATED,
        )
