"""Health endpoint and unknown-route envelope.

`docs/09-deployment.md` section 7 requires a lightweight health endpoint that
reports availability and database connectivity without leaking sensitive
details. `docs/12-error-handling-observability.md` section 5 additionally
requires that an unavailable *optional* dependency (the AI provider) must not
make the whole application appear unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter

from django.conf import settings
from django.db import connections
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.providers import build_llm_provider_from_env
from apps.common import errors
from apps.common.serializers import (
    ErrorEnvelopeSerializer,
    HealthDeepResponseSerializer,
    HealthLiveResponseSerializer,
    HealthReadyResponseSerializer,
    HealthResponseSerializer,
)

logger = logging.getLogger("app.errors")

SERVICE_NAME = "university-assistant-api"
# Baseline version string; release tagging is defined in docs/19-git-and-release.md.
APP_VERSION = "0.1.0"

STATE_OK = "ok"
STATE_UNAVAILABLE = "unavailable"
STATE_DEGRADED = "degraded"
STATE_EAGER = "eager"
# The AI provider adapter is a later phase (ADR-006). Reporting
# "not_configured" keeps the contract stable without pretending a dependency
# is healthy or unhealthy.
AI_PROVIDER_NOT_CONFIGURED = "not_configured"
AI_PROVIDER_MOCK = "mock"
AI_PROVIDER_CONFIGURED = "configured"


def _database_check() -> tuple[str, float | None]:
    """Return (state, latency_ms) for the required PostgreSQL connection.

    The driver error is logged with the request id and never returned; callers
    only receive the coarse state (docs/09 section 7, AGENTS.md section 9).
    """
    started = perf_counter()
    connection = connections["default"]
    try:
        connection.ensure_connection()
    except Exception:  # noqa: BLE001 - any backend failure must degrade health
        logger.exception("health_database_check_failed")
        try:
            connection.close()
        except Exception:  # noqa: BLE001 - closing a broken connection is best effort
            pass
        return STATE_UNAVAILABLE, None
    return STATE_OK, round((perf_counter() - started) * 1000, 2)


def _redis_check() -> tuple[str, float | None]:
    """Ping the Redis broker; the demo's required background dependency."""
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return STATE_EAGER, None
    started = perf_counter()
    try:
        import redis

        client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        try:
            client.ping()
        finally:
            client.close()
    except Exception:  # noqa: BLE001 - optional dependency must not leak details
        logger.warning("health_redis_check_failed", exc_info=True)
        return STATE_UNAVAILABLE, None
    return STATE_OK, round((perf_counter() - started) * 1000, 2)


def _worker_check() -> str:
    """Ask Celery whether at least one worker answers the ping control message."""
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return STATE_EAGER
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.ping(timeout=1.0)
    except Exception:  # noqa: BLE001 - broker/worker failures are reported as state
        logger.warning("health_worker_check_failed", exc_info=True)
        return STATE_UNAVAILABLE
    return STATE_OK if replies else STATE_UNAVAILABLE


def _storage_check() -> str:
    """Prove the document storage root is writable, without keeping a probe file."""
    root = Path(settings.DOCUMENT_STORAGE_ROOT)
    probe = root / ".health-probe"
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception:  # noqa: BLE001 - path and OS error stay in the logs
        logger.warning("health_storage_check_failed", exc_info=True)
        return STATE_UNAVAILABLE
    return STATE_OK


def _ai_provider_state() -> str:
    """Report configuration only; never call the external provider from health."""
    try:
        provider = build_llm_provider_from_env()
    except Exception:  # noqa: BLE001 - malformed provider config degrades to unconfigured
        logger.warning("health_ai_provider_config_invalid", exc_info=True)
        return AI_PROVIDER_NOT_CONFIGURED
    if provider is None:
        return AI_PROVIDER_NOT_CONFIGURED
    if provider.__class__.__name__ == "MockLLMProvider":
        return AI_PROVIDER_MOCK
    return AI_PROVIDER_CONFIGURED


def _base_payload(request) -> dict:
    return {
        "status": STATE_OK,
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "request_id": getattr(request, "request_id", "-"),
    }


@extend_schema(
    tags=["system"],
    summary="Liveness probe",
    responses={200: HealthLiveResponseSerializer},
)
class HealthLiveView(APIView):
    """``GET /health/live`` — process liveness only; no dependency checks."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(_base_payload(request))


@extend_schema(
    tags=["system"],
    summary="Readiness probe (required database)",
    responses={200: HealthReadyResponseSerializer, 503: ErrorEnvelopeSerializer},
)
class HealthReadyView(APIView):
    """``GET /health/ready`` — 200 only when the required database is reachable."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        database_state, latency_ms = _database_check()
        if database_state != STATE_OK:
            return Response(
                errors.build_error_payload(
                    errors.INTERNAL_ERROR,
                    "سرویس موقتاً در دسترس نیست.",
                    {"checks": {"database": database_state}},
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        payload = _base_payload(request)
        payload["checks"] = {
            "database": database_state,
            "database_latency_ms": latency_ms,
        }
        return Response(payload)


@extend_schema(
    tags=["system"],
    summary="Deep dependency health",
    responses={200: HealthDeepResponseSerializer, 503: ErrorEnvelopeSerializer},
)
class HealthDeepView(APIView):
    """``GET /health/deep`` — database, Redis, Celery worker, storage, AI config.

    Optional AI provider availability never fails the check (docs/12 section 5);
    the demo's required dependencies (database, broker, worker, storage) do.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        database_state, database_latency = _database_check()
        redis_state, redis_latency = _redis_check()
        worker_state = _worker_check()
        storage_state = _storage_check()
        ai_state = _ai_provider_state()

        required_states = [database_state, storage_state]
        if not settings.CELERY_TASK_ALWAYS_EAGER:
            required_states.extend([redis_state, worker_state])
        healthy = all(state == STATE_OK for state in required_states)

        payload = _base_payload(request)
        payload["status"] = STATE_OK if healthy else STATE_DEGRADED
        payload["checks"] = {
            "database": {
                "status": database_state,
                "latency_ms": database_latency,
            },
            "redis": {
                "status": redis_state,
                "latency_ms": redis_latency,
            },
            "worker": {"status": worker_state},
            "storage": {"status": storage_state},
            "ai_provider": {"status": ai_state},
        }
        http_status = (
            status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=http_status)


# Root-level aliases for the reverse proxy (config.urls). They are operational
# probes, not part of the consumer contract, so they stay out of openapi.yaml;
# the same handlers remain documented under /api/v1/health/... .
@extend_schema(exclude=True)
class RootHealthLiveView(HealthLiveView):
    pass


@extend_schema(exclude=True)
class RootHealthReadyView(HealthReadyView):
    pass


@extend_schema(exclude=True)
class RootHealthDeepView(HealthDeepView):
    pass


@extend_schema(
    tags=["system"],
    summary="Liveness and dependency health",
    responses={200: HealthResponseSerializer, 503: ErrorEnvelopeSerializer},
)
class HealthView(APIView):
    """``GET /api/v1/health/`` — unauthenticated liveness + database check."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        database_state, latency_ms = self._check_database(request)

        if database_state != STATE_OK:
            # The concrete driver error stays in the logs, never in the body.
            return Response(
                errors.build_error_payload(
                    errors.INTERNAL_ERROR,
                    "سرویس موقتاً در دسترس نیست.",
                    {"checks": {"database": database_state}},
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "status": STATE_OK,
                "service": SERVICE_NAME,
                "version": APP_VERSION,
                "request_id": getattr(request, "request_id", "-"),
                "checks": {
                    "database": database_state,
                    "database_latency_ms": latency_ms,
                    "ai_provider": AI_PROVIDER_NOT_CONFIGURED,
                },
            }
        )

    @staticmethod
    def _check_database(request) -> tuple[str, float | None]:
        # ``request`` is kept for the log context; the helper logs with the
        # request-context filter that supplies the correlation id.
        del request
        return _database_check()


@extend_schema(exclude=True)
class UnmatchedApiRouteView(APIView):
    """Return the documented NOT_FOUND envelope for unknown ``/api/v1/`` paths.

    Registered last in ``config.urls`` so unmatched API paths never fall back to
    Django's HTML error page.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def _not_found(self):
        raise errors.ApiError(
            errors.NOT_FOUND,
            "هیچ مسیر API با این نشانی مطابقت ندارد.",
            http_status=status.HTTP_404_NOT_FOUND,
        )

    def get(self, request, *args, **kwargs):
        self._not_found()

    def post(self, request, *args, **kwargs):
        self._not_found()

    def put(self, request, *args, **kwargs):
        self._not_found()

    def patch(self, request, *args, **kwargs):
        self._not_found()

    def delete(self, request, *args, **kwargs):
        self._not_found()

    def head(self, request, *args, **kwargs):
        self._not_found()

    def options(self, request, *args, **kwargs):
        self._not_found()
