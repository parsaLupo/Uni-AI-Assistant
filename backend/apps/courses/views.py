"""Course catalog endpoints.

Admin CRUD (`/admin/courses/`, `/admin/offerings/`, nested prerequisites and
schedules per docs/api/admin.md) plus public reads (`/courses/`,
`/course-offerings/`). Historical immutability (D4): rows of a past term
reject update/delete with 409 CONFLICT.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Count, ProtectedError, Q
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import AuditableViewSetMixin, record_audit
from apps.analytics.models import AuditAction
from apps.common.errors import CONFLICT, ApiError
from apps.common.metrics import ListObservabilityMixin
from apps.common.mixins import ConflictOnIntegrityMixin
from apps.common.persian import normalized_search
from apps.courses.models import ClassSchedule, Course, CourseOffering, CoursePrerequisite
from apps.courses.serializers import (
    ClassScheduleSerializer,
    CourseOfferingDetailSerializer,
    CourseOfferingSerializer,
    CoursePrerequisiteSerializer,
    CourseSerializer,
)

HISTORICAL_MESSAGE = "این ردیف به ترم گذشته تعلق دارد و سوابق تاریخی مصون‌اند؛ تغییر مجاز نیست."


def ensure_not_historical(instance) -> None:
    """Raise 409 when *instance* belongs to a past term (D4)."""
    offering = getattr(instance, "course_offering", None) or instance
    if getattr(offering, "is_historical", False):
        raise ApiError(CONFLICT, HISTORICAL_MESSAGE, http_status=409)


def with_enrolled_count(qs):
    return qs.annotate(
        enrolled_count=Count(
            "enrollments",
            filter=Q(enrollments__status__in=["PLANNED", "ENROLLED", "PASSED", "FAILED"]),
        )
    )


def _filter_offerings(qs, params, user=None):

    term = params.get("term")
    if term == "current":
        qs = qs.filter(term__is_current=True)
    elif term and term.isdigit():
        qs = qs.filter(term_id=int(term))
    course = params.get("course")
    if course:
        from django.db.models import Q

        # Course codes are numeric ("1916001") but are NOT ids — match both.
        code_q = Q(course__code=course)
        if course.isdigit():
            code_q |= Q(course_id=int(course))
        qs = qs.filter(code_q)
    professor = params.get("professor")
    if professor and professor.isdigit():
        qs = qs.filter(professor_id=int(professor))
    status_param = params.get("status")
    if status_param:
        qs = qs.filter(status=status_param)
    # Department scope for the student-account form: offerings of one major.
    department = params.get("department")
    if department and department.isdigit():
        qs = qs.filter(course__department_id=int(department))
    # Search across code + normalized title (courses.json keeps Persian titles).
    search = params.get("search")
    if search:
        qs = normalized_search(qs, search, "course__code", "course__normalized_title")
    return qs


class AdminCourseViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = Course.objects.select_related("department")
    serializer_class = CourseSerializer
    permission_classes = [IsAdmin]
    ordering_fields = ["code", "title", "credits", "created_at"]
    ordering = ["code"]

    def get_queryset(self):
        qs = super().get_queryset()
        department = self.request.query_params.get("department")
        if department and department.isdigit():
            qs = qs.filter(department_id=int(department))
        return normalized_search(
            qs, self.request.query_params.get("search"), "normalized_title"
        )

    def perform_destroy(self, instance):
        if instance.offerings.exists():
            raise ApiError(
                CONFLICT,
                "این درس ارائه شده است و قابل حذف نیست؛ غیرفعال‌اش کنید.",
                http_status=409,
            )
        super().perform_destroy(instance)


class AdminCourseOfferingViewSet(
    ListObservabilityMixin, ConflictOnIntegrityMixin, AuditableViewSetMixin, viewsets.ModelViewSet
):
    queryset = with_enrolled_count(
        CourseOffering.objects.select_related("course", "term", "professor")
    )
    serializer_class = CourseOfferingSerializer
    permission_classes = [IsAdmin]
    ordering_fields = ["course__code", "section_code", "capacity", "created_at"]
    ordering = ["course__code", "section_code"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseOfferingDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return _filter_offerings(super().get_queryset(), self.request.query_params)

    def perform_update(self, serializer):
        ensure_not_historical(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        ensure_not_historical(instance)
        try:
            super().perform_destroy(instance)
        except ProtectedError as exc:
            raise ApiError(
                CONFLICT,
                "این ارائه دارای ثبت‌نام/امتحان است؛ ابتدا آن‌ها را حذف یا لغو کنید.",
                http_status=409,
            ) from exc


class CourseViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public course catalog with prerequisites (docs/04 section 6)."""

    queryset = Course.objects.filter(active=True).select_related("department")
    serializer_class = CourseSerializer
    ordering_fields = ["code", "title", "credits"]
    ordering = ["code"]

    def get_queryset(self):
        qs = super().get_queryset()
        department = self.request.query_params.get("department")
        if department and department.isdigit():
            qs = qs.filter(department_id=int(department))
        credits = self.request.query_params.get("credits")
        if credits and credits.isdigit():
            qs = qs.filter(credits=int(credits))
        course_type = self.request.query_params.get("course_type")
        if course_type:
            qs = qs.filter(course_type__icontains=course_type)
        # Automatic department scoping for students.
        from apps.common.scoping import student_department_id

        dept_id = student_department_id(self.request.user)
        if dept_id is not None:
            qs = qs.filter(department_id=dept_id)
        return normalized_search(
            qs, self.request.query_params.get("search"), "normalized_title"
        )


class CourseOfferingViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public offerings (`?term=current|<id>`, `?course=<id|code>`, `?professor=<id>`)."""

    queryset = with_enrolled_count(
        CourseOffering.objects.select_related("course", "term", "professor").prefetch_related(
            "schedules"
        )
    )
    serializer_class = CourseOfferingDetailSerializer
    ordering_fields = ["course__code", "section_code"]
    ordering = ["course__code"]

    def get_queryset(self):
        return _filter_offerings(
            super().get_queryset(), self.request.query_params, self.request.user
        )


# --- Nested admin resources (docs/api/admin.md) ------------------------------


class AdminPrerequisiteListCreateView(APIView):
    """GET/POST /admin/courses/{id}/prerequisites/ — read/add edges of a course."""

    permission_classes = [IsAdmin]

    def _course(self, pk: str) -> Course:
        try:
            return Course.objects.get(pk=int(pk))
        except Course.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc

    @extend_schema(responses={200: CoursePrerequisiteSerializer(many=True)})
    def get(self, request, course_id: str):
        course = self._course(course_id)
        edges = course.prerequisite_edges.select_related("prerequisite_course", "course")
        return Response(CoursePrerequisiteSerializer(edges, many=True).data)

    @extend_schema(
        request=CoursePrerequisiteSerializer, responses={201: CoursePrerequisiteSerializer}
    )
    def post(self, request, course_id: str):
        course = self._course(course_id)
        serializer = CoursePrerequisiteSerializer(
            data={**request.data, "course_id": course.pk}
        )
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            # Duplicate edge / self-prerequisite — DB decides, contract says 409.
            raise ApiError(
                CONFLICT, "چنین پیش‌نیازی برای این درس ثبت شده است.", http_status=409
            ) from exc
        record_audit(request.user, AuditAction.CREATE, serializer.instance)
        return Response(serializer.data, status=201)


class AdminPrerequisiteDestroyView(APIView):
    """DELETE /admin/prerequisites/{id}/ — remove one edge."""

    permission_classes = [IsAdmin]

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk: str):
        try:
            edge = CoursePrerequisite.objects.get(pk=int(pk))
        except CoursePrerequisite.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc
        record_audit(request.user, AuditAction.DELETE, edge)
        edge.delete()
        return Response(status=204)


class AdminOfferingScheduleListCreateView(APIView):
    """GET/POST /admin/offerings/{id}/schedules/ — weekly meeting rows."""

    permission_classes = [IsAdmin]

    def _offering(self, pk: str) -> CourseOffering:
        try:
            return CourseOffering.objects.get(pk=int(pk))
        except CourseOffering.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc

    @extend_schema(responses={200: ClassScheduleSerializer(many=True)})
    def get(self, request, offering_id: str):
        offering = self._offering(offering_id)
        rows = offering.schedules.all()
        return Response(ClassScheduleSerializer(rows, many=True).data)

    @extend_schema(request=ClassScheduleSerializer, responses={201: ClassScheduleSerializer})
    def post(self, request, offering_id: str):
        offering = self._offering(offering_id)
        ensure_not_historical(offering)
        serializer = ClassScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course_offering=offering)
        record_audit(request.user, AuditAction.CREATE, serializer.instance)
        return Response(serializer.data, status=201)


class AdminScheduleDetailView(APIView):
    """PATCH/DELETE /admin/schedules/{id}/ — edit or remove one row."""

    permission_classes = [IsAdmin]

    @extend_schema(request=ClassScheduleSerializer, responses={200: ClassScheduleSerializer})
    def patch(self, request, pk: str):
        try:
            row = ClassSchedule.objects.get(pk=int(pk))
        except ClassSchedule.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc
        ensure_not_historical(row)
        serializer = ClassScheduleSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit(request.user, AuditAction.UPDATE, row)
        return Response(serializer.data)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk: str):
        try:
            row = ClassSchedule.objects.get(pk=int(pk))
        except ClassSchedule.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc
        ensure_not_historical(row)
        record_audit(request.user, AuditAction.DELETE, row)
        row.delete()
        return Response(status=204)
