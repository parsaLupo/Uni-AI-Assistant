"""Admin analytics aggregations + AI request telemetry (Phase 13).

Privacy rule (phase doc / checklist): analytics are *aggregate or
access-controlled* — the query layer itself never selects raw message
content. Every query below touches counts, means or small display fields
(document titles, audit metadata), never `Message.content`.

`docs/12`/A-10: computed on demand; no materialisation until proven slow.
"""

from __future__ import annotations

from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.analytics.models import AIRequestEvent, AuditLog

_OK = "OK"
_top_documents_size = 10


def record_ai_request(
    *,
    user=None,
    mode: str = "",
    outcome: str = _OK,
    latency_ms: int | None = None,
) -> None:
    """Persist one AI attempt; telemetry must never break the request."""
    try:
        AIRequestEvent.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            mode=(mode or "")[:32],
            outcome=(outcome or _OK)[:32],
            latency_ms=latency_ms,
        )
    except Exception:  # noqa: BLE001 — metrics are never load-bearing
        import logging

        logging.getLogger("app.analytics").exception("ai_request_event_failed")


def _mode_distribution() -> list[dict]:
    """Routed execution-mode counts for grounded answers (topic proxy).

    The only durable "topic" data in the application is the router's
    execution mode on assistant messages (docs/08 §2 modes); it is stored on
    `Message.retrieval_mode` and reported here. No message text is read.
    """
    from apps.conversations.models import Message

    rows = (
        Message.objects.filter(role=Message.Role.ASSISTANT)
        .exclude(retrieval_mode="")
        .values("retrieval_mode")
        .annotate(count=Count("pk"))
        .order_by("-count")
    )
    return [
        {"mode": row["retrieval_mode"], "count": row["count"]}
        for row in rows
    ]


def _top_documents(limit: int = _top_documents_size) -> list[dict]:
    """Most-referenced documents (how often each document grounded an answer)."""
    from apps.documents.models import Document

    rows = (
        Document.objects.annotate(citation_count=Count("chunks__message_sources"))
        .filter(citation_count__gt=0)
        .order_by("-citation_count", "title")[:limit]
        .values(
            "id",
            "title",
            "document_type",
            "academic_year",
            "citation_count",
        )
    )
    return list(rows)


def _ai_metrics() -> dict:
    """Usage/error counts + average latency from the telemetry table.

    Latency comes from the *completed* attempts (null on failures); message
    rows carry no content, only numbers. Both "since" boundaries are returned
    so the UI can label the coverage honestly (telemetry starts Phase 13).
    """
    totals = AIRequestEvent.objects.aggregate(
        total=Count("pk"),
        errors=Count("pk", filter=~Q(outcome=_OK)),
        latency=Avg("latency_ms", filter=Q(outcome=_OK)),
    )
    return {
        "total_requests": totals["total"] or 0,
        "error_count": totals["errors"] or 0,
        # round(2) per docs/12 latency reporting conventions; `is not None`
        # because a completed 0 ms attempt must still report 0, not n/a.
        "avg_latency_ms": (
            round(totals["latency"], 2) if totals["latency"] is not None else None
        ),
    }


def _user_metrics() -> dict:
    """Active users, from real accounts (no PII beyond role counts)."""
    from apps.accounts.models import User

    now = timezone.now()
    week_ago = now - timezone.timedelta(days=7)
    by_role = (
        User.objects.filter(is_active=True)
        .values("role")
        .annotate(count=Count("pk"))
        .order_by("-count")
    )
    return {
        "active_users": User.objects.filter(is_active=True).count(),
        "recently_active_users": User.objects.filter(
            is_active=True, last_login__gte=week_ago
        ).count(),
        "by_role": [
            {"role": row["role"], "count": row["count"]} for row in by_role
        ],
    }


def admin_dashboard() -> dict:
    """The aggregate-only payload behind `GET /admin/analytics/dashboard/`."""
    from apps.conversations.models import Message
    from apps.documents.models import Document

    week_ago = timezone.now() - timezone.timedelta(days=7)
    return {
        "users": _user_metrics(),
        "questions": {
            "total": Message.objects.filter(role=Message.Role.USER).count(),
            "last_7_days": Message.objects.filter(
                role=Message.Role.USER, created_at__gte=week_ago
            ).count(),
            "answers": Message.objects.filter(role=Message.Role.ASSISTANT).count(),
            "insufficient_evidence": Message.objects.filter(
                role=Message.Role.ASSISTANT, insufficient_evidence=True
            ).count(),
        },
        "topic_distribution": _mode_distribution(),
        "top_documents": _top_documents(),
        "ai": _ai_metrics(),
        "documents_total": Document.objects.count(),
        "generated_at": timezone.now().isoformat(),
    }


def audit_log_page(filters: dict | None = None):
    """Read-only, filterable audit rows (viewer, not an editor)."""
    filters = filters or {}
    qs = AuditLog.objects.select_related("actor").order_by("-created_at")
    entity_type = filters.get("entity_type")
    if entity_type:
        # Accept either the full label ("academics.Faculty") or bare model.
        qs = qs.filter(
            Q(entity_type=entity_type) | Q(entity_type__endswith=f".{entity_type}")
        )
    action = filters.get("action")
    if action:
        qs = qs.filter(action=action.upper())
    actor_id = filters.get("actor")
    if actor_id and actor_id.isdigit():
        qs = qs.filter(actor_id=int(actor_id))
    return qs
