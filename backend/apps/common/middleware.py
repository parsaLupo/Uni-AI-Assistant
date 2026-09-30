"""Request correlation and access logging.

`docs/12-error-handling-observability.md` sections 3 and 4 require a
correlation id per request plus structured logs containing the endpoint, status
code and latency, so that API and (later) AI-service logs can be joined.
"""

from __future__ import annotations

import logging
import re
import time
import uuid

logger = logging.getLogger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"
# An inbound header is untrusted input: unexpected values are replaced instead
# of being written straight into logs.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def resolve_request_id(inbound: str | None) -> str:
    if inbound and REQUEST_ID_PATTERN.match(inbound):
        return inbound
    return uuid.uuid4().hex


class RequestContextMiddleware:
    """Assign a correlation id, expose it, and log one line per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        started = time.perf_counter()

        response = self.get_response(request)

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response[REQUEST_ID_HEADER] = request.request_id
        logger.info(
            "http_request",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response


class RequestContextFilter(logging.Filter):
    """Guarantee the log keys exist outside request context too."""

    DEFAULTS = {
        "request_id": "-",
        "method": "-",
        "path": "-",
        "status_code": "-",
        "latency_ms": "-",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        for key, fallback in self.DEFAULTS.items():
            if not hasattr(record, key):
                setattr(record, key, fallback)
        return True
