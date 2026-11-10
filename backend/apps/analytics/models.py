"""Analytics domain (docs/02 §4.1 ownership; Phase 13 dashboard aggregations).

`docs/api/admin.md` makes every admin write auditable, while the analytics app
itself (aggregation, `/admin/analytics/`) is Phase 13. Phase 04 therefore ships
the model plus the write helper only — the entity lives in its designated app
from day one so no later migration has to move it.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"
    RETRY = "RETRY", "Retry"


class AuditLog(models.Model):
    """One row per audited write (actor, action, entity, ids)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=16, choices=AuditAction.choices)
    entity_type = models.CharField(max_length=64, db_index=True)
    entity_id = models.CharField(max_length=64)
    # before/after ids per docs/api/admin.md; extended freely later (Phase 13).
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}#{self.entity_id}"


class AIRequestEvent(models.Model):
    """One row per AI attempt (success or error), Phase 13 telemetry.

    Privacy: no question or answer text is stored — only the routed mode, the
    outcome code and the latency. Aggregations over this table feed the admin
    dashboard ("AI usage/error counts, average latency") without any path to
    raw conversation content.
    """

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["outcome", "created_at"], name="ai_outcome_idx"),
            models.Index(fields=["mode", "created_at"], name="ai_mode_idx"),
        ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_request_events",
    )
    # ExecutionMode value (STRUCTURED/RAG/HYBRID/…); "" when the pipeline
    # failed before routing.
    mode = models.CharField(max_length=32, blank=True, default="")
    # "OK" or the error-envelope code (AI_PROVIDER_ERROR, RETRIEVAL_ERROR, …).
    outcome = models.CharField(max_length=32, default="OK")
    # Null for failed attempts (no meaningful latency).
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return f"{self.mode or '-'} → {self.outcome} ({self.latency_ms or '—'}ms)"
