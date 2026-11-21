"""Student endpoints.

- `/students/me/` — onboarding (GET creates the empty profile row, PATCH fills
  university code + major; faculty derives from the chosen department).
- `/students/planner/` — the student's own term planner: offerings of the
  current term the student puts in, edits and removes (Enrollment status
  PLANNED). Formal enrollment/grades remain admin-managed.
- `/admin/students/`, `/admin/enrollments/` — docs/api/admin.md.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import AcademicTerm
from apps.accounts.models import Role
from apps.accounts.permissions import IsAdmin
from apps.ai.selection_explanation import SelectionExplanationService
from apps.analytics.audit import AuditableViewSetMixin
from apps.common.errors import (
    CONFLICT,
    NOT_FOUND,
    PERMISSION_DENIED,
    VALIDATION_ERROR,
    ApiError,
)
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.serializers import ErrorEnvelopeSerializer
from apps.courses.models import Course, CourseOffering
from apps.students.course_lookup import candidate_payload, resolve_course
from apps.students.course_selection import CourseSelectionEngine
from apps.students.models import Enrollment, EnrollmentStatus, StudentProfile
from apps.students.serializers import (
    CourseSelectionRequestSerializer,
    EnrollmentSerializer,
    PlannerItemSerializer,
    StudentProfileSerializer,
)

PLANNER_STATUSES = [EnrollmentStatus.PLANNED, EnrollmentStatus.ENROLLED]


def _get_profile(user, *, create: bool) -> StudentProfile:
    if user.role != Role.STUDENT:
        raise PermissionDenied("این بخش ویژه دانشجویان است.")
    profile = StudentProfile.objects.filter(user=user).first()
    if profile is None and create:
        profile = StudentProfile.objects.create(user=user)
    if profile is None:
        raise NotFound("پروفایل دانشجویی یافت نشد.")
    return profile


def _require_onboarding(profile: StudentProfile) -> None:
    if not profile.onboarding_complete:
        raise ApiError(
            CONFLICT,
            "ابتدا مشخصات دانشجویی (کد دانشجویی و رشته) را تکمیل کنید.",
            http_status=409,
        )


def _resolve_planner_term(params) -> AcademicTerm:
    term = params.get("term")
    if term and term.isdigit():
        try:
            return AcademicTerm.objects.get(pk=int(term))
        except AcademicTerm.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc
    current = AcademicTerm.objects.filter(is_current=True).first()
    if current is None:
        raise NotFound("ترم جاری یافت نشد.")
    return current


def _validate_planner_offering(offering: CourseOffering) -> None:
    from apps.courses.models import OfferingStatus

    if offering.status != OfferingStatus.OPEN:
        raise ApiError(CONFLICT, "این ارائه بسته یا لغوشده است.", http_status=409)
    if offering.term.is_past:
        raise ApiError(CONFLICT, "ارائه ترم گذشته در برنامه‌ریزی مجاز نیست.", http_status=409)


class StudentsMeView(APIView):
    """GET/PATCH /students/me/ — profile of the caller.

    Academic identity fields (student number, major, faculty, degree level,
    entry year, term number, GPA) are **registrar-owned**: students may read
    them but never write them — direct PATCH attempts are rejected with 403.
    Admins keep full write access via the admin student-profile surface.
    """

    # Fields a student may never self-edit (Part 1 of the profile spec).
    SELF_EDIT_PROTECTED_FIELDS = frozenset(
        {
            "student_number",
            "department_id",
            "faculty_id",
            "degree_level",
            "entry_year",
            "current_term_number",
            "current_gpa",
        }
    )
    PROTECTED_EDIT_MESSAGE = (
        "اطلاعات تحصیلی توسط مدیریت آموزشی ثبت می‌شود و از حساب دانشجو قابل تغییر نیست."
    )

    @extend_schema(responses=StudentProfileSerializer)
    def get(self, request):
        profile = _get_profile(request.user, create=True)
        return Response(StudentProfileSerializer(profile).data)

    @extend_schema(request=StudentProfileSerializer, responses=StudentProfileSerializer)
    def patch(self, request):
        profile = _get_profile(request.user, create=True)
        attempted = sorted(
            self.SELF_EDIT_PROTECTED_FIELDS.intersection(request.data or {})
        )
        if attempted:
            raise ApiError(
                PERMISSION_DENIED,
                self.PROTECTED_EDIT_MESSAGE,
                http_status=403,
            )
        serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            # Unique student_number decided by the database → documented 409.
            raise ApiError(
                CONFLICT,
                "کد دانشجویی قبلاً ثبت شده است.",
                http_status=409,
            ) from exc
        return Response(serializer.data)


class PlannerListCreateView(APIView):
    """GET/POST /students/planner/ — list or add planner items for a term."""

    @extend_schema(responses={200: PlannerItemSerializer(many=True)})
    def get(self, request):
        profile = _get_profile(request.user, create=True)
        term = _resolve_planner_term(request.query_params)
        rows = (
            Enrollment.objects.filter(
                student=profile, status__in=PLANNER_STATUSES, course_offering__term=term
            )
            .select_related(
                "course_offering__course",
                "course_offering__term",
                "course_offering__professor",
                "course_offering__exam",
            )
            .prefetch_related("course_offering__schedules")
        )
        return Response(PlannerItemSerializer(rows, many=True).data)

    @extend_schema(
        request=PlannerItemSerializer, responses={201: PlannerItemSerializer}
    )
    def post(self, request):
        profile = _get_profile(request.user, create=True)
        _require_onboarding(profile)
        serializer = PlannerItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offering = serializer.validated_data["course_offering"]
        _validate_planner_offering(offering)
        if Enrollment.objects.filter(student=profile, course_offering=offering).exists():
            raise ApiError(
                CONFLICT, "این درس هم‌اکنون در برنامه شماست.", http_status=409
            )
        try:
            with transaction.atomic():
                item = Enrollment.objects.create(
                    student=profile, course_offering=offering, status=EnrollmentStatus.PLANNED
                )
        except IntegrityError as exc:
            # DB unique (student, offering) backstop.
            raise ApiError(
                CONFLICT, "این درس هم‌اکنون در برنامه شماست.", http_status=409
            ) from exc
        return Response(PlannerItemSerializer(item).data, status=status.HTTP_201_CREATED)


class PlannerDetailView(APIView):
    """PATCH/DELETE /students/planner/{id}/ — edit (swap) or remove a row."""

    def _own_planned(self, request, pk: str) -> Enrollment:
        profile = _get_profile(request.user, create=True)
        try:
            item = Enrollment.objects.select_related(
                "course_offering__course", "course_offering__term"
            ).get(pk=int(pk), student=profile)
        except Enrollment.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc
        if item.status != EnrollmentStatus.PLANNED:
            raise ApiError(
                CONFLICT,
                "فقط ردیف‌های در حال برنامه‌ریزی قابل تغییر هستند؛ وضعیت نهایی را مدیر تغییر می‌دهد.",
                http_status=409,
            )
        return item

    @extend_schema(
        request=PlannerItemSerializer, responses={200: PlannerItemSerializer}
    )
    def patch(self, request, pk: str):
        item = self._own_planned(request, pk)
        serializer = PlannerItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        offering = serializer.validated_data.get("course_offering")
        if offering and offering.pk != item.course_offering_id:
            _validate_planner_offering(offering)
            if Enrollment.objects.filter(
                student=item.student, course_offering=offering
            ).exists():
                raise ApiError(
                    CONFLICT, "این درس هم‌اکنون در برنامه شماست.", http_status=409
                )
            item.course_offering = offering
            item.save(update_fields=["course_offering", "updated_at"])
        return Response(PlannerItemSerializer(item).data)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk: str):
        item = self._own_planned(request, pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminStudentProfileViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, viewsets.ModelViewSet
):
    """GET/PATCH /admin/students/ — profiles are created by onboarding/seed."""

    queryset = StudentProfile.objects.select_related("user", "department", "faculty")
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    ordering_fields = ["student_number", "created_at"]
    ordering = ["student_number"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        faculty = params.get("faculty")
        if faculty and faculty.isdigit():
            qs = qs.filter(faculty_id=int(faculty))
        department = params.get("department")
        if department and department.isdigit():
            qs = qs.filter(department_id=int(department))
        search = params.get("search")
        if search:
            qs = qs.filter(
                Q(student_number__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search.lower())
            )
        return qs


class AdminEnrollmentViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    """Manage enrollments/grades (`?student=`, `?term=`, `?status=`).

    Grade corrections on past terms stay allowed (audited carve-out, D4);
    deleting a historical row is not — use a terminal status instead.
    """

    queryset = Enrollment.objects.select_related(
        "student__user", "course_offering__course", "course_offering__term"
    )
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAdmin]
    ordering_fields = ["enrolled_at", "updated_at", "grade"]
    ordering = ["-enrolled_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        student = params.get("student")
        if student and student.isdigit():
            qs = qs.filter(student__user_id=int(student))
        term = params.get("term")
        if term == "current":
            qs = qs.filter(course_offering__term__is_current=True)
        elif term and term.isdigit():
            qs = qs.filter(course_offering__term_id=int(term))
        status_param = params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_destroy(self, instance):
        if instance.course_offering.term.is_past:
            raise ApiError(
                CONFLICT,
                "ثبت‌نام ترم گذشته قابل حذف نیست؛ وضعیت نهایی (حذف/انصراف/نمره) را ویرایش کنید.",
                http_status=409,
            )
        super().perform_destroy(instance)


@extend_schema(
    tags=["students"],
    summary="Course selection eligibility check",
    request=CourseSelectionRequestSerializer,
    responses={200: dict, 400: ErrorEnvelopeSerializer, 404: ErrorEnvelopeSerializer},
)
class CourseSelectionView(APIView):
    """POST /students/me/course-selection/ — Phase 11 eligibility check.

    The student types a course code *or* a Persian course name in
    ``course_query``; ``apps.students.course_lookup`` resolves it against the
    real catalog first (exact code, exact normalized title, unique containment,
    otherwise an ambiguity list / not-found). Only then does the pure rules
    engine (``apps.students.course_selection``) run on the *resolved* code, so
    the decision and every machine-readable rejection reason come from
    PostgreSQL records only and no rule is bypassed.

    The response embeds a deterministic composed explanation (AGENTS.md section
    8 — the LLM may explain, never decide; the assistant pipeline reuses
    ``SelectionExplanationService`` for its verdict-safe verbalisation).
    """

    def post(self, request):
        _get_profile(request.user, create=True)
        # `course_query` accepts a code or a Persian name; `course_code` stays
        # supported so existing clients keep working unchanged.
        raw_query = request.data.get("course_query")
        if not str(raw_query or "").strip():
            raw_query = request.data.get("course_code")
        course_query = str(raw_query or "").strip()
        if not course_query:
            raise ApiError(
                VALIDATION_ERROR,
                "کد یا نام درس نمی‌تواند خالی باشد.",
                http_status=400,
            )
        extra_codes = request.data.get("extra_course_codes") or []
        if not isinstance(extra_codes, list) or not all(
            isinstance(code, str) for code in extra_codes
        ):
            raise ApiError(
                VALIDATION_ERROR,
                "لیست درس‌های فرضی (extra_course_codes) نامعتبر است.",
                http_status=400,
            )
        for code in extra_codes:
            # Strict what-if lookup: the student gets an honest 400 instead of
            # a silently ignored unknown extra in the credit math.
            if not Course.objects.filter(code__iexact=str(code).strip()).exists():
                raise ApiError(
                    VALIDATION_ERROR,
                    f"درس فرضی با کد «{code}» یافت نشد.",
                    http_status=400,
                )
        match = resolve_course(course_query)
        if match.status == "not_found":
            # A clear, actionable message; the query stays in `details` for the
            # client but is never used as an internal trace.
            raise ApiError(
                NOT_FOUND,
                "درسی با این کد یا نام در پایگاه داده یافت نشد؛ "
                "کد درس یا نام دقیق آن را وارد کنید.",
                http_status=404,
                details={"query": course_query},
            )
        if match.status == "ambiguous":
            # Several catalog rows are plausible. Return them instead of
            # picking one: the engine must never run on an arbitrary course.
            return Response(
                {
                    "status": "ambiguous",
                    "query": course_query,
                    "candidates": [
                        candidate_payload(course) for course in match.candidates
                    ],
                    "total": match.total,
                }
            )

        assert match.course is not None  # "resolved" always carries the row
        course = match.course
        # The engine receives the *resolved* real code; every eligibility rule
        # and reason code is untouched by the lookup layer.
        decision = CourseSelectionEngine().evaluate(
            request.user,
            course.code,
            extra_course_codes=[str(code).strip() for code in extra_codes],
        )
        result = decision.to_dict()
        # Deterministic, always-available explanation; the engine verdict is
        # embedded so a client cannot contrast it with an LLM rewrite.
        explanation = SelectionExplanationService().explain(decision)
        result["explanation"] = {
            "text": explanation["text"],
            "source": explanation["source"],
            "engine_eligible": explanation["engine_eligible"],
        }
        result["status"] = "resolved"
        return Response(result)


