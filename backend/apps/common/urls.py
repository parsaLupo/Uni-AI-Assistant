"""Routes owned by the shared ``common`` app.

Mounted under ``/api/v1/`` by ``config.urls``.
"""

from django.urls import path

from apps.common import views

app_name = "common"

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    # Makes a bare ``/api/v1/`` request return the documented error envelope
    # instead of Django's HTML 404 page.
    path("", views.UnmatchedApiRouteView.as_view(), name="api-root-unmatched"),
]
