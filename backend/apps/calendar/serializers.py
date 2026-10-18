"""Calendar serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.academics.models import AcademicTerm
from apps.academics.serializers import AcademicTermSerializer
from apps.calendar.models import AcademicEvent
from apps.common.serializers import ConflictModelSerializer


class AcademicEventSerializer(ConflictModelSerializer):
    term = AcademicTermSerializer(read_only=True)
    term_id = serializers.PrimaryKeyRelatedField(
        source="term", queryset=AcademicTerm.objects.all(), write_only=True
    )

    class Meta:
        model = AcademicEvent
        fields = [
            "id",
            "term",
            "term_id",
            "title",
            "event_type",
            "starts_at",
            "ends_at",
            "description",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        # docs/03 §6: CHECK (starts_at < ends_at) — surfaced as a 400 with
        # field details instead of a raw database failure.
        starts = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts and ends and starts >= ends:
            raise serializers.ValidationError(
                {"ends_at": ["زمان پایان باید بعد از زمان شروع باشد."]}
            )
        return attrs
