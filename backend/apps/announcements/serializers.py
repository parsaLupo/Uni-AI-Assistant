"""Announcement serializers."""

from __future__ import annotations

from rest_framework import serializers

from apps.academics.models import AcademicTerm, Department, Faculty
from apps.academics.serializers import (
    AcademicTermSerializer,
    DepartmentSerializer,
    FacultySerializer,
)
from apps.announcements.models import Announcement
from apps.common.serializers import ConflictModelSerializer


class AnnouncementSerializer(ConflictModelSerializer):
    term = AcademicTermSerializer(read_only=True)
    term_id = serializers.PrimaryKeyRelatedField(
        source="term", queryset=AcademicTerm.objects.all(),
        write_only=True, required=False, allow_null=True,
    )
    audience_faculty = FacultySerializer(read_only=True)
    audience_faculty_id = serializers.PrimaryKeyRelatedField(
        source="audience_faculty", queryset=Faculty.objects.all(),
        write_only=True, required=False, allow_null=True,
    )
    audience_department = DepartmentSerializer(read_only=True)
    audience_department_id = serializers.PrimaryKeyRelatedField(
        source="audience_department", queryset=Department.objects.all(),
        write_only=True, required=False, allow_null=True,
    )

    class Meta:
        model = Announcement
        fields = [
            "id",
            "term",
            "term_id",
            "audience_faculty",
            "audience_faculty_id",
            "audience_department",
            "audience_department_id",
            "title",
            "body",
            "priority",
            "published_at",
            "expires_at",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
