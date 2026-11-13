"""Logging hygiene (docs/07-security.md section 2, Phase 15).

The access log records correlation id, method, path, status and latency —
nothing else. These tests prove that the sensitive payloads of the three most
sensitive endpoints (login password, refresh token, AI question text) never
appear in the emitted log records, and that every access record carries a
correlation id (`docs/12-error-handling-observability.md` section 4).
"""

from __future__ import annotations

import logging

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tokens import REFRESH_COOKIE_NAME

pytestmark = pytest.mark.django_db

PASSWORD = "S3cret-Password-1!"
QUESTION = "معدل ترم اول من چقدر است و چه دروثرایی افتاده دارم؟"


def _access_records(caplog):
    return [r for r in caplog.records if r.name == "app.access"]


def _run_logged_requests(caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        client = APIClient()

        # 1. Login: the request body carries a raw password.
        client.post(
            "/api/v1/auth/login/",
            {"email": "hygiene@example.edu", "password": PASSWORD},
            format="json",
        )

        # 2. Refresh: the refresh token travels in the cookie.
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.create_user(
            email="hygiene2@example.edu", password=PASSWORD
        )
        token = str(RefreshToken.for_user(user))
        client.cookies[REFRESH_COOKIE_NAME] = token
        client.post("/api/v1/auth/refresh/")

        # 3. AI ask: the question text is personal data.
        client.cookies.pop(REFRESH_COOKIE_NAME)
        client.force_authenticate(user=user)
        client.post("/api/v1/ai/ask/", {"question": QUESTION}, format="json")

    return token


def test_access_logs_never_contain_passwords_tokens_or_questions(caplog):
    token = _run_logged_requests(caplog)

    records = _access_records(caplog)
    assert len(records) >= 3, "expected one access record per request"

    for record in records:
        line = record.getMessage()
        assert PASSWORD not in line, f"password leaked into access log: {line}"
        assert token not in line, f"refresh token leaked into access log: {line}"
        assert QUESTION not in line, f"question text leaked into access log: {line}"


def test_every_access_record_carries_a_correlation_id(caplog):
    _run_logged_requests(caplog)

    for record in _access_records(caplog):
        assert record.request_id != "-"
        assert record.method in {"POST", "GET"}
        assert record.status_code
        assert record.latency_ms >= 0


def test_access_log_records_the_path_but_not_the_query_string(caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        client = APIClient()
        client.get("/api/v1/admin/documents/", {"search": "secret-term-1234"})

    lines = [r.getMessage() for r in _access_records(caplog)]
    assert lines, "access log missing"
    for line in lines:
        assert "secret-term-1234" not in line, f"query string leaked into log: {line}"
