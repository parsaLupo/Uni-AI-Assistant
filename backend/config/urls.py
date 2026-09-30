"""Root URL configuration.

All API routes live under ``/api/v1/`` (AGENTS.md section 6). The catch-all is
registered last so unmatched API paths still produce the documented error
envelope rather than an HTML page.
"""

from apps.common import views
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("apps.common.urls")),
    path(
        "api/v1/<path:unmatched>",
        views.UnmatchedApiRouteView.as_view(),
        name="api-unmatched",
    ),
]
