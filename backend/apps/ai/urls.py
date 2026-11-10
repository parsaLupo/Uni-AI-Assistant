"""AI routes mounted under /api/v1/."""

from django.urls import path

from apps.ai import views

urlpatterns = [
    path("ai/ask/", views.AskView.as_view(), name="ai-ask"),
    path("ai/ask/stream/", views.AskStreamView.as_view(), name="ai-ask-stream"),
]
