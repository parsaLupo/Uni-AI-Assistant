"""Notification serializers (Phase 12)."""

from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "link",
            "is_read",
            "read_at",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "read_at", "created_at"]
