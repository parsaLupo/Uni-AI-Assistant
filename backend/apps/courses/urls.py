"""Course catalog routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.courses import views

admin_router = DefaultRouter()
admin_router.register("courses", views.AdminCourseViewSet, basename="admin-courses")
admin_router.register(
    "offerings", views.AdminCourseOfferingViewSet, basename="admin-offerings"
)

public_router = DefaultRouter()
public_router.register("courses", views.CourseViewSet, basename="courses")
public_router.register(
    "course-offerings", views.CourseOfferingViewSet, basename="course-offerings"
)

urlpatterns = [
    path("admin/", include(admin_router.urls)),
    path(
        "admin/courses/<int:course_id>/prerequisites/",
        views.AdminPrerequisiteListCreateView.as_view(),
        name="admin-course-prerequisites",
    ),
    path(
        "admin/prerequisites/<int:pk>/",
        views.AdminPrerequisiteDestroyView.as_view(),
        name="admin-prerequisite-detail",
    ),
    path(
        "admin/offerings/<int:offering_id>/schedules/",
        views.AdminOfferingScheduleListCreateView.as_view(),
        name="admin-offering-schedules",
    ),
    path(
        "admin/schedules/<int:pk>/",
        views.AdminScheduleDetailView.as_view(),
        name="admin-schedule-detail",
    ),
    path("", include(public_router.urls)),
]
