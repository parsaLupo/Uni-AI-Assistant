"""Announcement routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.announcements import views

admin_router = DefaultRouter()
admin_router.register(
    "announcements", views.AdminAnnouncementViewSet, basename="admin-announcements"
)

public_router = DefaultRouter()
public_router.register(
    "announcements", views.AnnouncementViewSet, basename="announcements"
)

urlpatterns = [
    path("admin/", include(admin_router.urls)),
    path("", include(public_router.urls)),
]
