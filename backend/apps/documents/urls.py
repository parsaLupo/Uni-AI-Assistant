"""Document routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.documents import views

admin_router = DefaultRouter()
admin_router.register(
    "documents", views.AdminDocumentViewSet, basename="admin-documents"
)

urlpatterns = [
    path("admin/", include(admin_router.urls)),
]