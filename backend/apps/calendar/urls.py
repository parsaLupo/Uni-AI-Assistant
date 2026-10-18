"""Calendar routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.calendar import views

admin_router = DefaultRouter()
admin_router.register(
    "calendar/events", views.AdminAcademicEventViewSet, basename="admin-calendar-events"
)

public_router = DefaultRouter()
public_router.register(
    "calendar/events", views.AcademicEventViewSet, basename="calendar-events"
)

urlpatterns = [
    path("admin/", include(admin_router.urls)),
    path("", include(public_router.urls)),
]
