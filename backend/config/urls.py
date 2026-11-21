"""Root URL configuration.

All API routes live under ``/api/v1/`` (AGENTS.md section 6). The catch-all is
registered last so unmatched API paths still produce the documented error
envelope rather than an HTML page.
"""

from apps.common import views
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


class ApiSchemaView(SpectacularAPIView):
    """Schema endpoint (ADR-012).

    Excluded from its own output so the committed contract only describes
    endpoints consumers actually call.
    """

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


urlpatterns = [
    # Phase 16 release probes: the documented /health/... URLs are served by
    # the reverse proxy and answered by Django. Both the slashless and slash
    # forms exist so a probe never depends on APPEND_SLASH redirects.
    path("health/live", views.RootHealthLiveView.as_view(), name="root-health-live"),
    path("health/live/", views.RootHealthLiveView.as_view(), name="root-health-live-slash"),
    path("health/ready", views.RootHealthReadyView.as_view(), name="root-health-ready"),
    path("health/ready/", views.RootHealthReadyView.as_view(), name="root-health-ready-slash"),
    path("health/deep", views.RootHealthDeepView.as_view(), name="root-health-deep"),
    path("health/deep/", views.RootHealthDeepView.as_view(), name="root-health-deep-slash"),

    path("api/v1/", include("apps.common.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    # Phase 04 — core academic data (docs/02 section 4.1, docs/api/admin.md).
    path("api/v1/", include("apps.academics.urls")),
    path("api/v1/", include("apps.professors.urls")),
    path("api/v1/", include("apps.courses.urls")),
    path("api/v1/", include("apps.students.urls")),
    path("api/v1/", include("apps.calendar.urls")),
    path("api/v1/", include("apps.exams.urls")),
    path("api/v1/", include("apps.announcements.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.ai.urls")),
    path("api/v1/", include("apps.conversations.urls")),
    # Phase 13 — analytics + audit-log viewer (admin-only).
    path("api/v1/", include("apps.analytics.urls")),

    # Machine-readable contract (ADR-012): generated with drf-spectacular,
    # committed as openapi.yaml at the repository root, drift-checked in CI.
    # Registered before the catch-all so it is never shadowed.
    path("api/v1/schema/", ApiSchemaView.as_view(), name="schema"),
    path(
        "api/v1/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/<path:unmatched>",
        views.UnmatchedApiRouteView.as_view(),
        name="api-unmatched",
    ),
]
