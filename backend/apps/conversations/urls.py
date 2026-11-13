"""Conversation routes mounted under /api/v1/."""

from apps.conversations import views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("conversations", views.ConversationViewSet, basename="conversations")

urlpatterns = [
    path("", include(router.urls)),
]
