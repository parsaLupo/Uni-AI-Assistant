"""Bulk student import endpoints (admin-only).

Pipeline: download template → inspect → validate/preview → confirm → report.
The workbook is never persisted: every step receives the file again and the
preview's ``file_hash`` (sha256) is required on confirm, so the bytes that are
executed are provably the bytes the admin reviewed.
"""

from __future__ import annotations

import json
from typing import Any

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import student_import as domain
from apps.accounts.permissions import IsAdmin
from apps.analytics.models import AuditLog
from apps.common.errors import CONFLICT, VALIDATION_ERROR, ApiError

XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
TEMPLATE_FILENAME = "student-import-template.xlsx"
# Preview payload size guard: the full error list stays, row detail is capped.
PREVIEW_ROW_LIMIT = 200


class ImportFileSerializer(serializers.Serializer):
    """Inspect step: only the workbook."""

    file = serializers.FileField()


class ImportValidateSerializer(ImportFileSerializer):
    """Validate step: workbook + the admin's sheet/column mapping + mode."""

    mapping = serializers.CharField()
    mode = serializers.CharField(required=False, default=domain.MODE_CREATE_ONLY)


class ImportConfirmSerializer(ImportValidateSerializer):
    """Confirm step: the exact file/mapping that was previewed, plus its hash."""

    expected_hash = serializers.CharField(max_length=64)
    confirm = serializers.BooleanField()


class ImportReportRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    actor = serializers.CharField(allow_null=True)
    file_hash = serializers.CharField(allow_blank=True)
    mode = serializers.CharField(allow_blank=True)
    summary = serializers.DictField()


class ImportReportPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = ImportReportRowSerializer(many=True)


def _check_upload(upload) -> None:
    """Reject a missing or oversized workbook before reading it into memory."""
    if upload is None:
        raise ApiError(VALIDATION_ERROR, "فایلی انتخاب نشده است.", http_status=400)
    if upload.size is not None and upload.size > domain.MAX_FILE_BYTES:
        raise ApiError(
            VALIDATION_ERROR,
            "حجم فایل بیش از حد مجاز است (حداکثر ۵ مگابایت).",
            http_status=400,
        )


def _read_upload(request) -> bytes:
    """Extract and sanity-check the uploaded workbook bytes."""
    upload = request.FILES.get("file")
    _check_upload(upload)
    return upload.read()


def _parse_mapping(raw: str) -> dict[str, Any]:
    try:
        mapping = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ApiError(
            VALIDATION_ERROR,
            "نگاشت ستون‌ها معتبر نیست (JSON نامعتبر).",
            http_status=400,
        ) from exc
    if not isinstance(mapping, dict):
        raise ApiError(VALIDATION_ERROR, "نگاشت ستون‌ها معتبر نیست.", http_status=400)
    return mapping


def _validate_mode(mode: str) -> str:
    if mode not in domain.MODES:
        raise ApiError(VALIDATION_ERROR, "حالت واردکردن نامعتبر است.", http_status=400)
    return mode


def _trim_preview(report: dict) -> dict:
    """Keep the response bounded; the error list is always complete."""
    rows_total = 0
    for key in ("students", "passed_courses", "enrollments"):
        rows_total += len(report[key])
        report[key] = report[key][:PREVIEW_ROW_LIMIT]
    report["detail_limit"] = PREVIEW_ROW_LIMIT
    report["details_truncated"] = rows_total > PREVIEW_ROW_LIMIT * 3
    return report


class ImportTemplateView(APIView):
    """GET /api/v1/admin/students/import/template/ — the official .xlsx."""

    permission_classes = [IsAdmin]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="قالب رسمی بارگذاری گروهی دانشجویان (xlsx).",
            )
        }
    )
    def get(self, request):
        content = domain.build_template_workbook()
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{TEMPLATE_FILENAME}"'
        response["Cache-Control"] = "no-store"
        return response


class ImportInspectView(APIView):
    """POST /api/v1/admin/students/import/inspect/ — sheets, headers, samples."""

    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=ImportFileSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        parsed = domain.parse_workbook(_read_upload(request))
        return Response(domain.inspect_workbook(parsed))


class ImportValidateView(APIView):
    """POST /api/v1/admin/students/import/validate/ — dry-run preview."""

    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=ImportValidateSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = ImportValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mode = _validate_mode(serializer.validated_data["mode"])
        mapping = _parse_mapping(serializer.validated_data["mapping"])
        _check_upload(serializer.validated_data["file"])
        parsed = domain.parse_workbook(serializer.validated_data["file"].read())
        plan = domain.build_plan(parsed, mapping, mode)
        return Response(_trim_preview(plan.to_report()))


class ImportConfirmView(APIView):
    """POST /api/v1/admin/students/import/confirm/ — execute a validated plan."""

    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=ImportConfirmSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = ImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data["confirm"]:
            raise ApiError(
                VALIDATION_ERROR,
                "برای انجام واردکردن، تأیید نهایی الزامی است.",
                http_status=400,
            )
        mode = _validate_mode(data["mode"])
        mapping = _parse_mapping(data["mapping"])
        _check_upload(data["file"])
        content = data["file"].read()
        expected_hash = data["expected_hash"].strip().lower()
        actual_hash = domain.file_hash(content)
        if actual_hash != expected_hash:
            raise ApiError(
                CONFLICT,
                "فایل ارسال‌شده با فایلی که پیش‌نمایش شد یکسان نیست؛ دوباره بررسی کنید.",
                http_status=409,
            )
        parsed = domain.parse_workbook(content)
        if parsed.hash != expected_hash:
            raise ApiError(
                CONFLICT,
                "فایل ارسال‌شده با فایلی که پیش‌نمایش شد یکسان نیست؛ دوباره بررسی کنید.",
                http_status=409,
            )
        plan = domain.build_plan(parsed, mapping, mode)
        result = domain.execute_plan(plan, request.user)
        return Response(result, status=status.HTTP_200_OK)


class ImportReportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ImportReportsView(APIView):
    """GET /api/v1/admin/students/import/reports/ — audit trail of imports."""

    permission_classes = [IsAdmin]

    @extend_schema(responses={200: ImportReportPageSerializer})
    def get(self, request):
        queryset = AuditLog.objects.filter(entity_type="student_import").select_related(
            "actor"
        )
        paginator = ImportReportPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        rows = [
            {
                "id": entry.pk,
                "created_at": entry.created_at,
                "actor": entry.actor.email if entry.actor else None,
                "file_hash": entry.metadata.get("file_hash", ""),
                "mode": entry.metadata.get("mode", ""),
                "summary": entry.metadata.get("summary", {}),
            }
            for entry in page
        ]
        return paginator.get_paginated_response(rows)
