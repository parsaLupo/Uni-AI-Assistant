"""Phase 16 health probes: live / ready / deep.

The existing `/api/v1/health/` contract is covered by test_health.py; these
tests pin the new split probes, the no-detail-leak rule, and the fact that an
optional AI provider never takes the service down.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_live_probe_is_public_and_does_not_touch_dependencies(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "university-assistant-api"
    assert "checks" not in body


@pytest.mark.django_db
def test_probe_paths_work_at_root_and_under_the_api(client):
    for path in ("/health/live/", "/api/v1/health/live/"):
        assert client.get(path).status_code == 200
    for path in ("/health/ready/", "/api/v1/health/ready/"):
        assert client.get(path).status_code == 200
    for path in ("/health/deep/", "/api/v1/health/deep/"):
        assert client.get(path).status_code in {200, 503}


@pytest.mark.django_db
def test_ready_probe_reports_database_ok(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["checks"]["database"] == "ok"
    assert isinstance(body["checks"]["database_latency_ms"], float)


@pytest.mark.django_db
def test_ready_probe_degrades_to_503_without_leaking_the_driver_error(client):
    with patch("apps.common.views.connections") as connections:
        connections.__getitem__.return_value.ensure_connection.side_effect = RuntimeError(
            "host down / password mismatch"
        )
        response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["details"]["checks"]["database"] == "unavailable"
    assert "host down" not in json.dumps(body)
    assert "password" not in json.dumps(body)


@pytest.mark.django_db
def test_deep_probe_reports_all_required_dependencies(client, monkeypatch):
    # pytest settings run Celery eagerly, so Redis/worker report "eager"; storage
    # is patched to avoid writing during a unit test.
    monkeypatch.setattr("apps.common.views._storage_check", lambda: "ok")
    response = client.get("/health/deep")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    checks = body["checks"]
    assert checks["database"]["status"] == "ok"
    assert checks["redis"]["status"] == "eager"
    assert checks["worker"]["status"] == "eager"
    assert checks["storage"]["status"] == "ok"
    assert checks["ai_provider"]["status"] in {"mock", "configured", "not_configured"}


@pytest.mark.django_db
def test_deep_probe_degrades_when_database_or_storage_fails(client, monkeypatch):
    monkeypatch.setattr(
        "apps.common.views._database_check", lambda: ("unavailable", None)
    )
    monkeypatch.setattr("apps.common.views._storage_check", lambda: "ok")
    response = client.get("/health/deep")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"

    monkeypatch.setattr("apps.common.views._database_check", lambda: ("ok", 1.0))
    monkeypatch.setattr("apps.common.views._storage_check", lambda: "unavailable")
    response = client.get("/health/deep")
    assert response.status_code == 503


@pytest.mark.django_db
def test_optional_ai_provider_does_not_fail_the_deep_probe(client, monkeypatch):
    monkeypatch.setattr("apps.common.views._storage_check", lambda: "ok")
    monkeypatch.setattr(
        "apps.common.views._ai_provider_state", lambda: "not_configured"
    )
    response = client.get("/health/deep")
    assert response.status_code == 200
    assert response.json()["checks"]["ai_provider"]["status"] == "not_configured"


@pytest.mark.django_db
def test_deep_probe_never_exposes_internal_paths_or_driver_text(client, monkeypatch):
    monkeypatch.setattr(
        "apps.common.views._database_check", lambda: ("unavailable", None)
    )
    monkeypatch.setattr("apps.common.views._storage_check", lambda: "unavailable")
    monkeypatch.setattr("apps.common.views._redis_check", lambda: ("unavailable", None))
    with patch("apps.common.views._worker_check", return_value="unavailable"):
        response = client.get("/health/deep")
    text = response.content.decode()
    assert "Traceback" not in text
    assert "postgresql://" not in text
    assert "/app/" not in text
    assert response.json()["status"] == "degraded"
