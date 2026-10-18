"""Audit emission helpers and the DRF mixin that calls them on every write."""

from __future__ import annotations

from typing import Any

from apps.analytics.models import AuditAction, AuditLog


def record_audit(
    actor, action: str, instance, *, metadata: dict[str, Any] | None = None
) -> AuditLog:
    """Persist one audit row for *instance* (never raises into the request)."""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=instance._meta.label,
        entity_id=str(instance.pk) if instance.pk is not None else "",
        metadata=metadata or {},
    )


class AuditableViewSetMixin:
    """Hook create/update/delete of a ViewSet to the audit log."""

    def perform_create(self, serializer):
        instance = serializer.save()
        record_audit(self.request.user, AuditAction.CREATE, instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        record_audit(self.request.user, AuditAction.UPDATE, instance)

    def perform_destroy(self, instance):
        record_audit(self.request.user, AuditAction.DELETE, instance)
        instance.delete()
