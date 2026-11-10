"""Analytics serializers (Phase 13): small display-only shapes."""

from __future__ import annotations

from rest_framework import serializers

from apps.analytics.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "created_at",
            "actor",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "metadata",
        ]

    def to_representation(self, instance: AuditLog) -> dict:
        data = super().to_representation(instance)
        # ACTOR_EMAIL may be the only PII on the row; admins may see it, but
        # never show it for an anonymous/system actor (actor=None).
        if instance.actor is None or not self.context.get("include_actor_email"):
            data.pop("actor_email", None)
        return data


class AdminRoleCountSerializer(serializers.Serializer):
    role = serializers.CharField()
    count = serializers.IntegerField()


class AdminModeCountSerializer(serializers.Serializer):
    mode = serializers.CharField()
    count = serializers.IntegerField()


class AdminTopDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    document_type = serializers.CharField()
    academic_year = serializers.CharField()
    citation_count = serializers.IntegerField()
