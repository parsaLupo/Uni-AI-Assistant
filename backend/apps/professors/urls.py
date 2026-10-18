"""Professor routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.professors import views

admin_router = DefaultRouter()
admin_router.register("professors", views.AdminProfessorViewSet, basename="admin-professors")

public_router = DefaultRouter()
public_router.register("professors", views.ProfessorViewSet, basename="professors")

urlpatterns = [
    path("admin/", include(admin_router.urls)),
    path("", include(public_router.urls)),
]
