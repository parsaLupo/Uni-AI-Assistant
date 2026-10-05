"""Health endpoint and unknown-route envelope.

`docs/09-deployment.md` section 7 requires a lightweight health endpoint that
reports availability and database connectivity without leaking sensitive
details. `docs/12-error-handling-observability.md` section 5 additionally
requires that an unavailable *optional* dependency (the AI provider) must not
make the whole application appear unavailable.
"""

from __future__ import annotations

import logging
from time import perf_counter

from django.db import connections
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import errors
from apps.common.serializers import ErrorEnvelopeSerializer, HealthResponseSerializer

logger = logging.getLogger("app.errors")

SERVICE_NAME = "university-assistant-api"
# Baseline version string; release tagging is defined in docs/19-git-and-release.md.
APP_VERSION = "0.1.0"

STATE_OK = "ok"
STATE_UNAVAILABLE = "unavailable"
# The AI provider adapter is a later phase (ADR-006). Reporting
# "not_configured" keeps the contract stable without pretending a dependency
# is healthy or unhealthy.
AI_PROVIDER_NOT_CONFIGURED = "not_configured"


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
        started = perf_counter()
        try:
            connections["default"].ensure_connection()
        except Exception:  # noqa: BLE001 - any backend failure must degrade health
            logger.exception(
                "health_database_check_failed",
                extra={"request_id": getattr(request, "request_id", "-")},
            )
            return STATE_UNAVAILABLE, None
        return STATE_OK, round((perf_counter() - started) * 1000, 2)


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
