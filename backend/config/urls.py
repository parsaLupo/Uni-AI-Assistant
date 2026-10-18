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
