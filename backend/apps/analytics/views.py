"""Admin analytics endpoints (Phase 13, `/admin/analytics/*`).

- `GET /admin/analytics/dashboard/` — the aggregate-only dashboard payload.
- `GET /admin/analytics/audit-log/` — read-only viewer over the append-only
  `AuditLog` (filters: `?entity_type=`, `?action=`, `?actor=`).

Both are `IsAdmin`-gated: students (and professors) are rejected server-side.
Views contain no business rules — permission, pagination, serializers only;
the aggregation maths lives in `apps.analytics.services` and no query touches
raw message content (privacy rule enforced in the query layer, not the UI).
"""

from __future__ import annotations

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.analytics.serializers import AuditLogSerializer
from apps.analytics.services import admin_dashboard, audit_log_page
from apps.common.pagination import StandardResultsSetPagination


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["admin"],
        summary="داشبورد تحلیلی مدیر (فقط داده تجمعی)",
        responses={200: inline_serializer(name="AdminDashboard", fields={})},
    )
    def get(self, request):
        return Response(admin_dashboard())


class AdminAuditLogView(APIView):
    """Read-only audit-log viewer over the append-only source (no writes)."""

    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=["admin"],
        summary="مشاهده‌گر گزارش حسابرسی (فقط خواندنی)",
        parameters=[
            OpenApiParameter(
                "entity_type", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                "action", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                "actor", OpenApiTypes.INT, OpenApiParameter.QUERY, required=False
            ),
        ],
        responses={200: AuditLogSerializer(many=True)},
    )
    def get(self, request):
        qs = audit_log_page(
            {
                "entity_type": request.query_params.get("entity_type") or "",
                "action": request.query_params.get("action") or "",
                "actor": request.query_params.get("actor") or "",
            }
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = AuditLogSerializer(
            page, many=True, context={"include_actor_email": True}
        )
        return paginator.get_paginated_response(serializer.data)
