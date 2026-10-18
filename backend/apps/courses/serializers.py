"""Course/offerings serializers.

Reads nest related objects; writes take `<fk>_id` (Phase 04 convention).
"""

from __future__ import annotations

from rest_framework import serializers

from apps.academics.models import AcademicTerm, Department
from apps.academics.serializers import AcademicTermSerializer, DepartmentSerializer
from apps.common.serializers import ConflictModelSerializer
from apps.courses.models import (
    ClassSchedule,
    Course,
    CourseOffering,
    CoursePrerequisite,
)
from apps.exams.serializers import ExamSerializer
from apps.professors.models import Professor
from apps.professors.serializers import ProfessorBriefSerializer


class ClassScheduleSerializer(ConflictModelSerializer):
    weekday_display = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = ClassSchedule
        fields = [
            "id",
            "weekday",
            "weekday_display",
            "start_time",
            "end_time",
            "classroom",
        ]


class PrerequisiteCourseSerializer(serializers.ModelSerializer):
    """Compact course view used inside prerequisite lists."""

    class Meta:
        model = Course
        fields = ["id", "code", "title", "credits"]


class CourseSerializer(ConflictModelSerializer):
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.all(), write_only=True
    )
    prerequisites = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "credits",
            "course_type",
            "active",
            "department",
            "department_id",
            "prerequisites",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_prerequisites(self, obj) -> list[dict]:
        edges = obj.prerequisite_edges.select_related("prerequisite_course").all()
        return PrerequisiteCourseSerializer(
            [edge.prerequisite_course for edge in edges], many=True
        ).data


class CoursePrerequisiteSerializer(ConflictModelSerializer):
    course = PrerequisiteCourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        source="course", queryset=Course.objects.all(), write_only=True
    )
    prerequisite_course = PrerequisiteCourseSerializer(read_only=True)
    prerequisite_course_id = serializers.PrimaryKeyRelatedField(
        source="prerequisite_course", queryset=Course.objects.all(), write_only=True
    )

    class Meta:
        model = CoursePrerequisite
        fields = [
            "id",
            "course",
            "course_id",
            "prerequisite_course",
            "prerequisite_course_id",
            "created_at",
        ]


class CourseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "title", "credits", "course_type"]


class CourseOfferingSerializer(ConflictModelSerializer):
    course = CourseBriefSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        source="course", queryset=Course.objects.all(), write_only=True
    )
    term = AcademicTermSerializer(read_only=True)
    term_id = serializers.PrimaryKeyRelatedField(
        source="term", queryset=AcademicTerm.objects.all(), write_only=True
    )
    professor = ProfessorBriefSerializer(read_only=True)
    professor_id = serializers.PrimaryKeyRelatedField(
        source="professor", queryset=Professor.objects.all(),
        write_only=True, required=False, allow_null=True,
    )
    enrolled_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseOffering
        fields = [
            "id",
            "course",
            "course_id",
            "term",
            "term_id",
            "professor",
            "professor_id",
            "section_code",
            "capacity",
            "status",
            "enrolled_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_enrolled_count(self, obj) -> int:
        # Views annotate `enrolled_count`; freshly created instances have none.
        return getattr(obj, "enrolled_count", 0) or 0


class CourseOfferingDetailSerializer(CourseOfferingSerializer):
    schedules = ClassScheduleSerializer(many=True, read_only=True)
    exam = ExamSerializer(read_only=True)

    class Meta(CourseOfferingSerializer.Meta):
        fields = CourseOfferingSerializer.Meta.fields + ["schedules", "exam"]
