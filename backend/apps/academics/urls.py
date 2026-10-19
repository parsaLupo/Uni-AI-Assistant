"""Academic-structure routes mounted under /api/v1/ (docs/api/admin.md)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academics import views

admin_router = DefaultRouter()
admin_router.register("faculties", views.AdminFacultyViewSet, basename="admin-faculties")
admin_router.register("departments", views.AdminDepartmentViewSet, basename="admin-departments")
admin_router.register("terms", views.AdminTermViewSet, basename="admin-terms")

public_router = DefaultRouter()
public_router.register("terms", views.TermViewSet, basename="terms")
public_router.register("departments", views.DepartmentViewSet, basename="departments")

urlpatterns = [
    path("admin/", include(admin_router.urls)),
    path("", include(public_router.urls)),
]
