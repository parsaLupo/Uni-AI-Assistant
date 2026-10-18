"""Student routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.students import views

admin_router = DefaultRouter()
admin_router.register("students", views.AdminStudentProfileViewSet, basename="admin-students")
admin_router.register(
    "enrollments", views.AdminEnrollmentViewSet, basename="admin-enrollments"
)

urlpatterns = [
    path("admin/", include(admin_router.urls)),
    path("students/me/", views.StudentsMeView.as_view(), name="students-me"),
    path("students/planner/", views.PlannerListCreateView.as_view(), name="students-planner"),
    path(
        "students/planner/<int:pk>/",
        views.PlannerDetailView.as_view(),
        name="students-planner-detail",
    ),
]
