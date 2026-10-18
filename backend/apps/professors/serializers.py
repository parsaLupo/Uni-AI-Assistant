"""Professor serializers (read nested, write `<fk>_id` — Phase 04 convention)."""

from __future__ import annotations

from rest_framework import serializers

from apps.academics.models import Department
from apps.academics.serializers import DepartmentSerializer
from apps.common.serializers import ConflictModelSerializer
from apps.professors.models import Professor


class ProfessorSerializer(ConflictModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.all(), write_only=True
    )

    class Meta:
        model = Professor
        fields = [
            "id",
            "department",
            "department_id",
            "first_name",
            "last_name",
            "academic_title",
            "email",
            "office",
            "website",
            "bio",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ProfessorBriefSerializer(serializers.ModelSerializer):
    """Compact professor used nested inside offerings/exams."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = ["id", "first_name", "last_name", "full_name", "academic_title"]

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"
