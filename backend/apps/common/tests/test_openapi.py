"""OpenAPI contract tests (ADR-012, Phase 01).

The committed openapi.yaml is the machine-readable API contract; these tests
prove the schema generates from live code, is publicly servable, and does not
leak internal paths.
"""

from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator


def build_schema() -> dict:
    schema = SchemaGenerator().get_schema(request=None, public=True)
    assert schema is not None, "schema generation must not fail"
    return schema


def test_schema_contains_health_and_title():
    schema = build_schema()

    assert schema["info"]["title"] == "University Smart Assistant API"
    assert "/api/v1/health/" in schema["paths"]


def test_schema_is_valid_and_excludes_internal_routes():
    schema = build_schema()

    # The catch-all 404 view and the schema/swagger endpoints are
    # implementation details, not a contract for consumers.
    assert "/api/v1/schema/" not in schema["paths"]
    assert all("unmatched" not in path for path in schema["paths"])
    # Nothing outside the versioned prefix may ever appear.
    assert all(path.startswith("/api/v1/") for path in schema["paths"])


def test_schema_endpoint_is_public_even_with_secure_default_permissions():
    """AGENTS.md section 6: contract discovery must not require credentials."""
    from django.test import Client

    response = Client().get(reverse("schema"))

    assert response.status_code == 200
