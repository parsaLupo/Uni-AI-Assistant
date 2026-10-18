"""Student serializers: onboarding profile, admin enrollment, planner items.

Onboarding (user-requested flow) collects name/last name at registration
(kept on `User`) and the academic attributes here: «کد دانشجویی»
(student_number) and «رشته/-major» (department; faculty is derived from it).
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.academics.models import Department, Faculty
from apps.academics.serializers import FacultySerializer
from apps.accounts.models import User
from apps.common.serializers import ConflictModelSerializer
from apps.courses.models import CourseOffering
from apps.courses.serializers import (
    CourseOfferingDetailSerializer,
    CourseOfferingSerializer,
)
from apps.students.models import DegreeLevel, Enrollment, EnrollmentStatus, StudentProfile


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class StudentDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code"]


class StudentProfileSerializer(ConflictModelSerializer):
    user = UserBriefSerializer(read_only=True)
    department = StudentDepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.filter(is_active=True),
        write_only=True, required=False, allow_null=True,
    )
    faculty = FacultySerializer(read_only=True)
    faculty_id = serializers.PrimaryKeyRelatedField(
        source="faculty", queryset=Faculty.objects.filter(is_active=True),
        write_only=True, required=False, allow_null=True,
    )
    onboarding_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "student_number",
            "department",
            "department_id",
            "faculty",
            "faculty_id",
            "degree_level",
            "entry_year",
            "current_term_number",
            "current_gpa",
            "onboarding_complete",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["current_term_number", "current_gpa", "created_at", "updated_at"]

    def validate_degree_level(self, value):
        if value and value not in DegreeLevel.values:
            raise serializers.ValidationError("مقطع تحصیلی نامعتبر است.")
        return value

    def validate(self, attrs):
        # Picking a major implies its faculty unless explicitly chosen.
        if attrs.get("department") and not attrs.get("faculty") and self.instance is None:
            attrs["faculty"] = attrs["department"].faculty
        elif attrs.get("department") and "faculty" not in attrs:
            attrs["faculty"] = attrs["department"].faculty
        return attrs


class StudentProfileBriefSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = ["id", "user", "student_number"]


class EnrollmentSerializer(ConflictModelSerializer):
    student = StudentProfileBriefSerializer(read_only=True)
    student_id = serializers.PrimaryKeyRelatedField(
        source="student", queryset=StudentProfile.objects.all(), write_only=True
    )
    course_offering = CourseOfferingSerializer(read_only=True)
    course_offering_id = serializers.PrimaryKeyRelatedField(
        source="course_offering", queryset=CourseOffering.objects.all(), write_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "student",
            "student_id",
            "course_offering",
            "course_offering_id",
            "status",
            "grade",
            "enrolled_at",
            "updated_at",
        ]
        read_only_fields = ["enrolled_at", "updated_at"]

    def validate_grade(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("20")):
            raise serializers.ValidationError("نمره باید بین ۰ تا ۲۰ باشد.")
        return value

    def validate(self, attrs):
        status_value = attrs.get("status", getattr(self.instance, "status", None))
        grade = attrs.get("grade", getattr(self.instance, "grade", None))
        if status_value and grade is not None and status_value not in EnrollmentStatus.gradeable():
            raise serializers.ValidationError(
                {"grade": "نمره فقط برای وضعیت قبول/مردود مجاز است."}
            )
        if status_value in EnrollmentStatus.gradeable() and grade is None:
            raise serializers.ValidationError(
                {"grade": "برای وضعیت قبول/مردود، نمره الزامی است."}
            )
        return attrs


class PlannerItemSerializer(serializers.ModelSerializer):
    """One row of the student's own planner (Enrollment)."""

    course_offering = CourseOfferingDetailSerializer(read_only=True)
    course_offering_id = serializers.PrimaryKeyRelatedField(
        source="course_offering", queryset=CourseOffering.objects.all(), write_only=True
    )
    total_credits = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "course_offering",
            "course_offering_id",
            "status",
            "total_credits",
            "enrolled_at",
            "updated_at",
        ]
        read_only_fields = ["status", "enrolled_at", "updated_at"]

    def get_total_credits(self, obj) -> int:
        return obj.course_offering.course.credits
