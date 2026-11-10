"""AI question endpoints (Phase 09)."""

from __future__ import annotations

import json
import time

from django.http import StreamingHttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.answer import AnswerService
from apps.ai.providers import build_llm_provider_from_env
from apps.analytics.services import record_ai_request
from apps.common.errors import VALIDATION_ERROR, ApiError


def _service() -> AnswerService:
    return AnswerService(provider=build_llm_provider_from_env())


class AskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        if not question:
            raise ApiError(VALIDATION_ERROR, "پرسش نمی‌تواند خالی باشد.", http_status=400)
        message_id = request.data.get("message_id")
        started = time.perf_counter()
        try:
            result = _service().answer(
                question, user=request.user, message_id=message_id
            )
        except ApiError as exc:
            # Phase 13 telemetry: one row per attempt, no question/answer text.
            record_ai_request(
                user=request.user,
                outcome=exc.code,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            raise
        record_ai_request(
            user=request.user,
            mode=result.get("mode") or "",
            outcome="OK",
            latency_ms=result.get("latency_ms"),
        )
        return Response(result)


class AskStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question = (request.data.get("question") or "").strip()
        if not question:
            raise ApiError(VALIDATION_ERROR, "پرسش نمی‌تواند خالی باشد.", http_status=400)
        message_id = request.data.get("message_id")

        def event_stream():
            started = time.perf_counter()
            last_mode = ""
            try:
                for event in _service().answer_stream(
                    question, user=request.user, message_id=message_id
                ):
                    if event.get("event") == "done":
                        last_mode = (event.get("data") or {}).get("mode") or ""
                        record_ai_request(
                            user=request.user,
                            mode=last_mode,
                            outcome="OK",
                            latency_ms=(event.get("data") or {}).get("latency_ms"),
                        )
                    yield f"event: {event['event']}\n"
                    yield f"data: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
            except ApiError as exc:
                record_ai_request(
                    user=request.user,
                    mode=last_mode,
                    outcome=exc.code,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                error_data = json.dumps(
                    {"code": exc.code, "message": str(exc)}, ensure_ascii=False
                )
                yield "event: error\n"
                yield f"data: {error_data}\n\n"
            except Exception:  # noqa: BLE001
                record_ai_request(
                    user=request.user,
                    mode=last_mode,
                    outcome="AI_PROVIDER_ERROR",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                error_data = json.dumps(
                    {
                        "code": "AI_PROVIDER_ERROR",
                        "message": "سرویس هوش مصنوعی موقتاً در دسترس نیست.",
                    },
                    ensure_ascii=False,
                )
                yield "event: error\n"
                yield f"data: {error_data}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
