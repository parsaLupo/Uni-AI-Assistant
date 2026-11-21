"""Routes owned by the shared ``common`` app.

Mounted under ``/api/v1/`` by ``config.urls``.
"""

from django.urls import path

from apps.common import views

app_name = "common"

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    # Phase 16: distinct liveness / readiness / deep dependency probes. The
    # root-level aliases in config.urls make the documented /health/... paths
    # work through nginx; these remain under the versioned API for clients.
    path("health/live/", views.HealthLiveView.as_view(), name="health-live"),
    path("health/ready/", views.HealthReadyView.as_view(), name="health-ready"),
    path("health/deep/", views.HealthDeepView.as_view(), name="health-deep"),
    # Makes a bare ``/api/v1/`` request return the documented error envelope
    # instead of Django's HTML 404 page.
    path("", views.UnmatchedApiRouteView.as_view(), name="api-root-unmatched"),
]
