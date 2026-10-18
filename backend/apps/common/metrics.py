"""List-endpoint observability (V-06).

`docs/12` requires structured logs for API endpoints; the checklist adds the
specific Phase 04 gate: *query count and latency logged for list endpoints*.
One INFO line per list request on the `app.metrics` logger, carrying the same
request id as the access log so the two can be joined.

Query counting uses `connection.execute_wrapper`, which works with
`DEBUG=False` (unlike `connection.queries`) and therefore measures the real
production path.
"""

from __future__ import annotations

import logging
import time

from django.db import connection

logger = logging.getLogger("app.metrics")


class ListObservabilityMixin:
    """Override ``list`` to log duration, SQL query count and result count."""

    def list(self, request, *args, **kwargs):
        query_count = 0

        def counter(execute, sql, params, many, context):
            nonlocal query_count
            query_count += 1
            return execute(sql, params, many, context)

        started = time.perf_counter()
        with connection.execute_wrapper(counter):
            response = super().list(request, *args, **kwargs)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        results = response.data.get("results") if isinstance(response.data, dict) else None
        result_count = len(results) if results is not None else None
        logger.info(
            "list_endpoint",
            extra={
                "request_id": getattr(request, "request_id", "-"),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "latency_ms": duration_ms,
                "query_count": query_count,
                "result_count": result_count,
            },
        )
        return response
