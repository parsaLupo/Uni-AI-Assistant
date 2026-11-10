"""Notification endpoints (Phase 12, `/notifications/*`).

- `GET /notifications/` — the caller's *active* (non-expired) notifications,
  newest first; `?unread=true` narrows to unread. Pagination per AGENTS.md §6
  (the list grows with usage).
- `GET /notifications/unread-count/` — badge count of active unread rows.
- `POST /notifications/mark-all-read/` — mark all unread active rows read.
- `POST /notifications/{id}/mark-read/` — persist one row's read state.

Authorisation is enforced by queryset scoping (never a client check): another
user's notification pk is a 404, matching the planner's anti-enumeration
contract.
"""

from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardResultsSetPagination
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import active_notifications, unread_count

_UNREAD_COUNT_RESPONSE = inline_serializer(
    name="UnreadCountResponse",
    fields={"unread_count": serializers.IntegerField()},
)
_MARK_ALL_READ_RESPONSE = inline_serializer(
    name="MarkAllReadResponse",
    fields={"updated": serializers.IntegerField()},
)


def _own_notification(request, pk: str) -> Notification:
    notification = Notification.objects.filter(user=request.user, pk=int(pk or 0)).first()
    if notification is None:
        raise NotFound("یادآوری موردنظر یافت نشد.")
    return notification


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @extend_schema(
        tags=["notifications"],
        summary="یادآوری‌های فعال کاربر",
        parameters=[
            OpenApiParameter(
                "unread", OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False
            )
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request):
        qs = active_notifications(request.user)
        if (request.query_params.get("unread") or "").lower() in {"1", "true", "yes"}:
            qs = qs.filter(is_read=False)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["notifications"],
        summary="تعداد یادآوری‌های ناخوانده",
        responses={200: _UNREAD_COUNT_RESPONSE},
    )
    def get(self, request):
        return Response({"unread_count": unread_count(request.user)})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["notifications"],
        summary="علامت‌گذاری یک یادآوری به‌عنوان خوانده‌شده",
        request=None,
        responses={200: NotificationSerializer},
    )
    def post(self, request, pk: str):
        notification = _own_notification(request, pk)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.updated_at = notification.read_at
        notification.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response(NotificationSerializer(notification).data)


class MarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["notifications"],
        summary="علامت‌گذاری همه یادآوری‌های فعال به‌عنوان خوانده‌شده",
        request=None,
        responses={200: _MARK_ALL_READ_RESPONSE},
    )
    def post(self, request):
        now = timezone.now()
        updated = (
            active_notifications(request.user)
            .filter(is_read=False)
            .update(is_read=True, read_at=now, updated_at=now)
        )
        return Response({"updated": updated})
