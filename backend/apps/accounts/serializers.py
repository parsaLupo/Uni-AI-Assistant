"""Serializer contract for the auth endpoints (docs/api/auth.md, ADR-014)."""

from __future__ import annotations

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.academics.models import AcademicTerm, Department
from apps.accounts.models import Role, User
from apps.common.errors import CONFLICT, ApiError
from apps.common.persian import normalize_persian
from apps.courses.models import Course, CourseOffering, OfferingStatus
from apps.students.models import DegreeLevel, Enrollment, EnrollmentStatus, StudentProfile

DUPLICATE_EMAIL_MESSAGE = "کاربری با این ایمیل قبلاً ثبت شده است."
DUPLICATE_STUDENT_NUMBER_MESSAGE = "کد دانشجویی قبلاً ثبت شده است."
INVALID_ENTRY_YEAR_MESSAGE = "سال ورود باید عددی ۴ رقمی معتبر باشد."


def normalize_email(value: str) -> str:
    """One normalization for register, login and admin create (ADR-014)."""
    return value.strip().lower()


def validate_password_value(value: str) -> str:
    """Run Django's validators; surface failures as Persian field errors."""
    try:
        password_validation.validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class LoginUserSerializer(serializers.Serializer):
    """Minimal user summary returned by login/register/refresh (docs/api/auth.md)."""

    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.ChoiceField(choices=Role.choices, read_only=True)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active")
        read_only_fields = ("id", "email", "role", "is_active")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        email = normalize_email(value)
        if User.objects.filter(email=email).exists():
            raise ApiError(CONFLICT, DUPLICATE_EMAIL_MESSAGE, http_status=409)
        return email

    def validate_password(self, value: str) -> str:
        return validate_password_value(value)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        return normalize_email(value)


class PasswordChangeSerializer(serializers.Serializer):
    """POST /auth/password-change/ — the only self-service credential change."""

    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        return validate_password_value(value)


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Admin-provisioned account (ADR-014 decision 2: privileged roles only here).

    For ``role=STUDENT`` the academic identity fields are required and the
    historical/current enrollments the admin selects are created atomically
    with the account (user + StudentProfile + Enrollment rows); any failure
    rolls the whole creation back (Part 4 of the profile-improvement spec).
    """

    password = serializers.CharField(write_only=True, trim_whitespace=False)
    # Silence ModelSerializer's generated UniqueValidator: duplicates must reach
    # validate_email so the contract's 409 CONFLICT (not DRF's 400) is returned.
    email = serializers.EmailField(validators=[])

    # ── Student academic identity (required when role=STUDENT) ──────────────
    student_number = serializers.CharField(required=False, allow_blank=True, max_length=16)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.filter(is_active=True),
        required=False,
    )
    degree_level = serializers.ChoiceField(
        choices=DegreeLevel.choices, required=False, allow_blank=True
    )
    entry_year = serializers.CharField(required=False, allow_blank=True, max_length=9)
    # Historical passes: course codes from the selected department's catalog.
    passed_course_codes = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    # Current-term takes: existing CourseOffering ids of the active term.
    current_offering_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "student_number",
            "department_id",
            "degree_level",
            "entry_year",
            "passed_course_codes",
            "current_offering_ids",
        )
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        email = normalize_email(value)
        if User.objects.filter(email=email).exists():
            raise ApiError(CONFLICT, DUPLICATE_EMAIL_MESSAGE, http_status=409)
        return email

    def validate_password(self, value: str) -> str:
        return validate_password_value(value)

    def validate_student_number(self, value: str) -> str:
        number = normalize_persian(value or "").strip()
        if not number:
            return ""
        if StudentProfile.objects.filter(student_number=number).exists():
            raise ApiError(CONFLICT, DUPLICATE_STUDENT_NUMBER_MESSAGE, http_status=409)
        return number

    def validate_entry_year(self, value: str) -> str:
        year = normalize_persian(value or "").strip()
        if not year:
            return ""
        if not (year.isdigit() and len(year) == 4 and 1350 <= int(year) <= 1420):
            raise serializers.ValidationError(INVALID_ENTRY_YEAR_MESSAGE)
        return year

    def validate(self, attrs):
        role = attrs.get("role", Role.STUDENT)
        provided = [
            field
            for field in (
                "student_number",
                "department",
                "degree_level",
                "entry_year",
                "passed_course_codes",
                "current_offering_ids",
            )
            if attrs.get(field)
        ]
        if role != Role.STUDENT:
            if provided:
                raise serializers.ValidationError(
                    {"student_fields": "فیلدهای تحصیلی فقط برای نقش دانشجو مجاز است."}
                )
            return attrs

        missing = [
            STUDENT_FIELD_LABELS[field]
            for field in ("student_number", "department", "degree_level", "entry_year")
            if not attrs.get(field)
        ]
        if missing:
            raise serializers.ValidationError(
                {
                    "student_fields": "برای نقش دانشجو تکمیل این فیلدها الزامی است: "
                    + "، ".join(missing)
                }
            )

        codes: list[str] = []
        for raw in attrs.get("passed_course_codes") or []:
            code = normalize_persian(str(raw or "")).strip()
            if code and code not in codes:
                codes.append(code)
        department = attrs["department"]
        courses = {
            c.code: c
            for c in Course.objects.filter(
                code__in=codes, department=department, active=True
            )
        }
        unknown = [code for code in codes if code not in courses]
        if unknown:
            raise serializers.ValidationError(
                {
                    "passed_course_codes": [
                        f"درس {code} در رشتهٔ انتخاب‌شده یافت نشد." for code in unknown
                    ]
                }
            )
        attrs["passed_courses"] = [courses[code] for code in codes]

        offering_ids: list[int] = []
        for raw in attrs.get("current_offering_ids") or []:
            if raw and raw not in offering_ids:
                offering_ids.append(raw)
        offerings = {
            o.pk: o
            for o in CourseOffering.objects.filter(pk__in=offering_ids).select_related(
                "course", "term"
            )
        }
        unknown_ids = [pk for pk in offering_ids if pk not in offerings]
        if unknown_ids:
            raise serializers.ValidationError(
                {"current_offering_ids": "ارائهٔ انتخاب‌شدهٔ درس یافت نشد."}
            )
        passed_codes = set(courses)
        seen_course_codes: set[str] = set()
        errors: list[str] = []
        for pk in offering_ids:
            offering = offerings[pk]
            course = offering.course
            label = f"{course.code} ({course.title})"
            if not offering.term.is_current:
                errors.append(f"ارائهٔ درس {label} به ترم جاری تعلق ندارد.")
            elif course.department_id != department.pk:
                errors.append(f"درس {label} به رشتهٔ انتخاب‌شده تعلق ندارد.")
            elif course.code in passed_codes:
                errors.append(f"درس {label} نمی‌تواند هم‌زمان پاس‌شده و در حال اخذ باشد.")
            elif course.code in seen_course_codes:
                errors.append(f"درس {label} در دو گروه هم‌زمان انتخاب شده است.")
            seen_course_codes.add(course.code)
        if errors:
            raise serializers.ValidationError({"current_offering_ids": errors})
        attrs["current_offerings"] = [offerings[pk] for pk in offering_ids]
        return attrs

    def create(self, validated_data):
        passed_courses = validated_data.pop("passed_courses", [])
        current_offerings = validated_data.pop("current_offerings", [])
        validated_data.pop("passed_course_codes", None)
        validated_data.pop("current_offering_ids", None)
        student_number = validated_data.pop("student_number", "")
        entry_year = validated_data.pop("entry_year", "")
        department = validated_data.pop("department", None)
        role = validated_data.get("role", Role.STUDENT)
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=validated_data["email"],
                    password=validated_data["password"],
                    first_name=validated_data.get("first_name", ""),
                    last_name=validated_data.get("last_name", ""),
                    role=role,
                )
                if role == Role.STUDENT:
                    profile = StudentProfile.objects.create(
                        user=user,
                        student_number=student_number,
                        department=department,
                        faculty=department.faculty,
                        degree_level=validated_data.pop("degree_level", ""),
                        entry_year=entry_year,
                    )
                    _create_passed_enrollments(profile, passed_courses, entry_year)
                    for offering in current_offerings:
                        Enrollment.objects.get_or_create(
                            student=profile,
                            course_offering=offering,
                            defaults={"status": EnrollmentStatus.ENROLLED},
                        )
        except IntegrityError as exc:
            # Unique races (email/student number) decided by the database → 409.
            raise ApiError(CONFLICT, DUPLICATE_EMAIL_MESSAGE, http_status=409) from exc
        return user


STUDENT_FIELD_LABELS = {
    "student_number": "کد دانشجویی",
    "department": "رشته تحصیلی",
    "degree_level": "مقطع",
    "entry_year": "سال ورود",
}


def _create_passed_enrollments(profile, courses, entry_year: str) -> None:
    """Historical PASSED enrollments for admin-selected courses.

    The enrollment must belong to a *past* term the student could have taken
    the course in (their entry year or later). When the dataset has no
    historical offering for a course, a closed historical offering row
    (section 01, capacity 0) is created — the same convention the academic
    history import uses. Grades are never invented: PASSED rows carry no
    grade until a registrar value exists (the engine keys on status only).
    """
    past_terms = list(AcademicTerm.objects.filter(is_current=False).order_by("starts_at"))
    # Terms the student could have passed courses in; when the entry year is
    # beyond every recorded term, the latest past term stays the least-wrong
    # historical slot.
    eligible = [t for t in past_terms if t.academic_year >= entry_year] or (
        past_terms[-1:]
    )
    for course in courses:
        offering = None
        for term in eligible:
            offering = (
                CourseOffering.objects.filter(course=course, term=term)
                .order_by("section_code")
                .first()
            )
            if offering is not None:
                break
        if offering is None and eligible:
            offering = CourseOffering.objects.create(
                course=course,
                term=eligible[0],
                section_code="01",
                capacity=0,
                status=OfferingStatus.CLOSED,
            )
        if offering is None:
            # No historical term exists at all — nothing can be fabricated.
            continue
        Enrollment.objects.get_or_create(
            student=profile,
            course_offering=offering,
            defaults={"status": EnrollmentStatus.PASSED},
        )


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Email is immutable; role changes are guarded in the view (see docs/api/admin.md)."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active")
        read_only_fields = ("id", "email")
