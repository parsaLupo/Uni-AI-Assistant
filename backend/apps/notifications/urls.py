"""Notification routes mounted under /api/v1/."""

from django.urls import path

from apps.notifications import views

urlpatterns = [
    path("notifications/", views.NotificationListView.as_view(), name="notifications-list"),
    path(
        "notifications/unread-count/",
        views.UnreadCountView.as_view(),
        name="notifications-unread-count",
    ),
    path(
        "notifications/mark-all-read/",
        views.MarkAllReadView.as_view(),
        name="notifications-mark-all-read",
    ),
    path(
        "notifications/<int:pk>/mark-read/",
        views.MarkReadView.as_view(),
        name="notifications-mark-read",
    ),
]
