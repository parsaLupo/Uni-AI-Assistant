"""Exam serializers.

The nested offering view is defined here (not imported from courses.serializers)
to keep the import graph acyclic — courses imports *this* module for the
offering detail payload.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import ConflictModelSerializer
from apps.courses.models import CourseOffering
from apps.exams.models import Exam


class ExamOfferingBriefSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    section_code = serializers.CharField(read_only=True)

    class Meta:
        model = CourseOffering
        fields = ["id", "course_code", "course_title", "section_code"]


class ExamSerializer(ConflictModelSerializer):
    course_offering = ExamOfferingBriefSerializer(read_only=True)
    course_offering_id = serializers.PrimaryKeyRelatedField(
        source="course_offering",
        queryset=CourseOffering.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Exam
        fields = [
            "id",
            "course_offering",
            "course_offering_id",
            "starts_at",
            "ends_at",
            "classroom",
            "status",
            "last_updated_at",
            "created_at",
        ]
        read_only_fields = ["last_updated_at", "created_at"]

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.course_offering.is_historical:
            raise serializers.ValidationError(
                "امتحان ترم گذشته تاریخی است و قابل تغییر نیست."
            )
        return attrs
