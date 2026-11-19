"""Auth and user-management routes (docs/api/auth.md, docs/api/admin.md)."""

from django.urls import path

from apps.accounts import import_views, views

app_name = "accounts"

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path(
        "auth/password-change/",
        views.PasswordChangeView.as_view(),
        name="auth-password-change",
    ),
    path("admin/users/", views.AdminUserListCreateView.as_view(), name="admin-users"),
    path(
        "admin/users/<int:pk>/",
        views.AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
    # Bulk student import (docs/api/admin.md): stateless, one file per step.
    path(
        "admin/students/import/template/",
        import_views.ImportTemplateView.as_view(),
        name="admin-student-import-template",
    ),
    path(
        "admin/students/import/inspect/",
        import_views.ImportInspectView.as_view(),
        name="admin-student-import-inspect",
    ),
    path(
        "admin/students/import/validate/",
        import_views.ImportValidateView.as_view(),
        name="admin-student-import-validate",
    ),
    path(
        "admin/students/import/confirm/",
        import_views.ImportConfirmView.as_view(),
        name="admin-student-import-confirm",
    ),
    path(
        "admin/students/import/reports/",
        import_views.ImportReportsView.as_view(),
        name="admin-student-import-reports",
    ),
]
