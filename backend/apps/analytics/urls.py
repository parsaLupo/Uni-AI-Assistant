"""Analytics routes mounted under /api/v1/ (admin-only; Phase 13)."""

from django.urls import path

from apps.analytics import views

urlpatterns = [
    path(
        "admin/analytics/dashboard/",
        views.AdminDashboardView.as_view(),
        name="admin-analytics-dashboard",
    ),
    path(
        "admin/analytics/audit-log/",
        views.AdminAuditLogView.as_view(),
        name="admin-analytics-audit-log",
    ),
]
