"""Academic-structure serializers.

Convention used across Phase 04: reads expose the related object nested under
`<fk>`; writes accept the id under `<fk>_id` — unambiguous in the contract and
in Swagger.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.academics.models import AcademicTerm, Department, Faculty
from apps.common.serializers import ConflictModelSerializer


class FacultySerializer(ConflictModelSerializer):
    class Meta:
        model = Faculty
        fields = [
            "id",
            "name",
            "code",
            "website",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class DepartmentSerializer(ConflictModelSerializer):
    faculty = FacultySerializer(read_only=True)
    faculty_id = serializers.PrimaryKeyRelatedField(
        source="faculty", queryset=Faculty.objects.all(), write_only=True
    )

    class Meta:
        model = Department
        fields = [
            "id",
            "faculty",
            "faculty_id",
            "name",
            "code",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AcademicTermSerializer(ConflictModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = [
            "id",
            "name",
            "academic_year",
            "semester_type",
            "starts_at",
            "ends_at",
            "is_current",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
