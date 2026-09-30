"""Baseline tests: health endpoint, error envelope, correlation id.

These are the Phase 00 verification gate required by
`docs/08-testing-strategy.md` section 6 — no feature behaviour is asserted,
only the contracts the later phases depend on.
"""

import json

import pytest
from django.conf import settings

from apps.common import errors


@pytest.mark.django_db
def test_health_reports_ok_and_database_connectivity(client):
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "university-assistant-api"
    assert body["checks"]["database"] == "ok"
    assert isinstance(body["checks"]["database_latency_ms"], float)


@pytest.mark.django_db
def test_health_is_public_even_with_secure_default_permissions(client):
    """docs/09-deployment.md section 7: health must not require credentials."""
    response = client.get("/api/v1/health/")

    assert response.status_code != 401
    assert response.status_code == 200


@pytest.mark.django_db
def test_an_unavailable_ai_provider_does_not_take_the_service_down(client):
    """docs/12-error-handling-observability.md section 5."""
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json()["checks"]["ai_provider"] == "not_configured"


def test_health_503_when_database_is_down_without_leaking_details(monkeypatch, client):
    from django.db.backends.base.base import BaseDatabaseWrapper

    def _boom(self):
        raise RuntimeError("host down / password mismatch")

    monkeypatch.setattr(BaseDatabaseWrapper, "ensure_connection", _boom)

    response = client.get("/api/v1/health/")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == errors.INTERNAL_ERROR
    assert body["error"]["details"]["checks"]["database"] == "unavailable"
    # AGENTS.md section 9 / docs/09 section 7: internals never reach the client.
    assert "host down" not in json.dumps(body)


@pytest.mark.django_db
def test_unknown_api_path_uses_the_documented_error_envelope(client):
    response = client.get("/api/v1/not-a-real-route/")

    assert response.status_code == 404
    body = response.json()
    assert list(body) == ["error"]
    assert list(body["error"]) == ["code", "message", "details"]
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_bare_api_version_root_uses_the_documented_error_envelope(client):
    response = client.get("/api/v1/")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_method_not_allowed_returns_envelope_instead_of_html(client):
    response = client.put("/api/v1/health/", data={}, content_type="application/json")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == errors.METHOD_NOT_ALLOWED


def test_correlation_id_is_generated_and_returned(client):
    response = client.get("/api/v1/health/")

    issued = response["X-Request-ID"]
    assert issued
    assert len(issued) == 32


def test_inbound_correlation_id_is_echoed_for_tracing(client):
    response = client.get("/api/v1/health/", headers={"X-Request-ID": "trace-abc_123"})

    assert response["X-Request-ID"] == "trace-abc_123"


def test_unsafe_inbound_correlation_id_is_replaced(client):
    """Untrusted header values must not be written into logs unchanged."""
    response = client.get("/api/v1/health/", headers={"X-Request-ID": "x" * 200})

    assert len(response["X-Request-ID"]) == 32


def test_error_taxonomy_from_docs_is_implemented():
    documented = {
        "VALIDATION_ERROR",
        "AUTHENTICATION_REQUIRED",
        "PERMISSION_DENIED",
        "NOT_FOUND",
        "CONFLICT",
        "RATE_LIMITED",
        "AI_PROVIDER_ERROR",
        "RETRIEVAL_ERROR",
        "DOCUMENT_PROCESSING_ERROR",
        "INTERNAL_ERROR",
    }
    implemented = {
        errors.VALIDATION_ERROR,
        errors.AUTHENTICATION_REQUIRED,
        errors.PERMISSION_DENIED,
        errors.NOT_FOUND,
        errors.CONFLICT,
        errors.RATE_LIMITED,
        errors.AI_PROVIDER_ERROR,
        errors.RETRIEVAL_ERROR,
        errors.DOCUMENT_PROCESSING_ERROR,
        errors.INTERNAL_ERROR,
    }
    assert documented == implemented


def test_pagination_contract_is_configured_globally():
    """docs/04-api-specification.md section 4: page/page_size, one shape."""
    rest_settings = settings.REST_FRAMEWORK

    assert rest_settings["PAGE_SIZE"] == 20
    assert rest_settings["DEFAULT_PAGINATION_CLASS"].endswith("StandardResultsSetPagination")
    expected_auth = ["rest_framework.permissions.IsAuthenticated"]
    assert rest_settings["DEFAULT_PERMISSION_CLASSES"] == expected_auth


def is_persian_text(value: str) -> bool:
    """True when the string contains Persian/Arabic script characters."""
    return any("\u0600" <= char <= "\u06ff" for char in value)


def test_default_language_is_persian():
    """AGENTS.md "Language & Localization": primary language is fa-IR."""
    assert settings.LANGUAGE_CODE.startswith("fa")


@pytest.mark.django_db
def test_error_message_shown_to_users_is_persian(client):
    """docs/11: error messages shown to users must be Persian, codes stay English."""
    response = client.get("/api/v1/not-a-real-route/")
    body = response.json()["error"]

    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "هیچ مسیر API با این نشانی مطابقت ندارد."
    assert is_persian_text(body["message"])


def test_framework_validation_details_are_persian():
    """Field-level validation text must not reach users in English.

    Relies on the `fa` catalog DRF ships (no extra dependency, ADR-010).
    """
    from django.utils import translation
    from rest_framework import serializers

    class _SampleSerializer(serializers.Serializer):
        title = serializers.CharField()

    with translation.override("fa"):
        serializer = _SampleSerializer(data={})
        assert not serializer.is_valid()
        message = str(serializer.errors["title"][0])

    assert message != "This field is required."
    assert is_persian_text(message)
