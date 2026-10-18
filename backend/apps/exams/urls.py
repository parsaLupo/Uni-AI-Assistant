"""Exam routes mounted under /api/v1/."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.exams import views

public_router = DefaultRouter()
public_router.register("exams", views.ExamViewSet, basename="exams")

urlpatterns = [
    path(
        "admin/offerings/<int:offering_id>/exam/",
        views.AdminOfferingExamView.as_view(),
        name="admin-offering-exam",
    ),
    path("", include(public_router.urls)),
]
