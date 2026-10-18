"""Exam endpoints: admin set-exam-per-offering + public /exams/ list.

The admin surface is the nested resource from docs/api/admin.md —
`GET/PUT/PATCH /admin/offerings/{id}/exam/` (one exam per offering, DB-level).
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.analytics.audit import record_audit
from apps.analytics.models import AuditAction
from apps.common.metrics import ListObservabilityMixin
from apps.courses.models import CourseOffering
from apps.courses.views import ensure_not_historical
from apps.exams.models import Exam
from apps.exams.serializers import ExamSerializer


def _filter_exams(qs, params):
    term = params.get("term")
    if term == "current":
        qs = qs.filter(course_offering__term__is_current=True)
    elif term and term.isdigit():
        qs = qs.filter(course_offering__term_id=int(term))
    course = params.get("course")
    if course:
        if course.isdigit():
            qs = qs.filter(course_offering__course_id=int(course))
        else:
            qs = qs.filter(course_offering__course__code=course)
    return qs


class ExamViewSet(ListObservabilityMixin, viewsets.ReadOnlyModelViewSet):
    """Public exam schedule (docs/04 section 6)."""

    queryset = Exam.objects.select_related(
        "course_offering__course", "course_offering__term", "course_offering__professor"
    )
    serializer_class = ExamSerializer
    ordering_fields = ["starts_at", "created_at"]
    ordering = ["starts_at"]

    def get_queryset(self):
        return _filter_exams(super().get_queryset(), self.request.query_params)


class AdminOfferingExamView(APIView):
    """GET/PUT/PATCH /admin/offerings/{id}/exam/ — set the exam of an offering."""

    permission_classes = [IsAdmin]

    def _offering(self, pk: str) -> CourseOffering:
        try:
            return CourseOffering.objects.get(pk=int(pk))
        except CourseOffering.DoesNotExist as exc:
            raise NotFound("منبع موردنظر یافت نشد.") from exc

    @extend_schema(responses={200: ExamSerializer})
    def get(self, request, offering_id: str):
        offering = self._offering(offering_id)
        try:
            exam = offering.exam
        except Exam.DoesNotExist as exc:
            raise NotFound("برای این ارائه هنوز امتحانی ثبت نشده است.") from exc
        return Response(ExamSerializer(exam).data)

    @extend_schema(request=ExamSerializer, responses={201: ExamSerializer})
    def put(self, request, offering_id: str):
        return self._write(request, offering_id, partial=False)

    @extend_schema(request=ExamSerializer, responses={200: ExamSerializer})
    def patch(self, request, offering_id: str):
        return self._write(request, offering_id, partial=True)

    def _write(self, request, offering_id: str, *, partial: bool):
        offering = self._offering(offering_id)
        ensure_not_historical(offering)
        exam = Exam.objects.filter(course_offering=offering).first()
        if exam is None:
            serializer = ExamSerializer(data={**request.data, "course_offering_id": offering.pk})
        else:
            serializer = ExamSerializer(exam, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        created = serializer.instance is None
        serializer.save()
        record_audit(
            request.user, AuditAction.CREATE if created else AuditAction.UPDATE, serializer.instance
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=response_status)
