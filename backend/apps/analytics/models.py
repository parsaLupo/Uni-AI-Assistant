"""Audit domain (docs/07 section 7; entity ownership per docs/02 section 4.1).

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
