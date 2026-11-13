"""Rate limit on the admin document upload endpoint (Phase 15).

`RATE_UPLOAD` bounds how many documents one admin can push into the ingestion
pipeline per minute — a burst of uploads is the cheapest way to load the
processing queue and the embedding path. The budget applies to `create` and
`retry` (both enqueue processing); reads and metadata updates are untouched.

DRF snapshots `DEFAULT_THROTTLE_RATES` onto `SimpleRateThrottle.THROTTLE_RATES`
at first import, so tests patch the class attribute directly (see the AI
throttle tests for the same reasoning).
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.common.throttles import UploadRateThrottle
from apps.documents.models import Document

pytestmark = pytest.mark.django_db

TEST_PASSWORD = "Str0ng-Passw0rd!"
PDF_BYTES = b"%PDF-1.4\n%%EOF"


@pytest.fixture
def upload_rate(monkeypatch):
    """Set the effective `upload` rate for the current test."""

    def _set(rate: str):
        rates = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "upload": rate}
        monkeypatch.setattr(UploadRateThrottle, "THROTTLE_RATES", rates, raising=False)

    return _set


def _admin(email="upload-throttle@example.edu"):
    return User.objects.create_user(
        email=email, password=TEST_PASSWORD, role="ADMIN"
    )


def _client(user):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _upload(client, name="doc.pdf"):
    return client.post(
        "/api/v1/admin/documents/",
        {
            "title": f"Regulation {name}",
            "document_type": "regulation",
            "academic_year": "1405-1406",
            "file": SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf"),
        },
        format="multipart",
    )


def test_upload_is_rate_limited_after_the_configured_budget(upload_rate):
    upload_rate("2/min")
    admin = _admin()
    client = _client(admin)

    assert _upload(client, "one.pdf").status_code == 202
    assert _upload(client, "two.pdf").status_code == 202

    throttled = _upload(client, "three.pdf")

    assert throttled.status_code == 429
    error = throttled.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert isinstance(error.get("retry_after_seconds", 0), (int, float))


def test_budget_is_per_admin_not_global(upload_rate):
    upload_rate("2/min")
    first = _admin()
    second = _admin("second-admin@example.edu")

    assert _upload(_client(first), "a.pdf").status_code == 202
    assert _upload(_client(first), "b.pdf").status_code == 202
    assert _upload(_client(first), "c.pdf").status_code == 429

    # The second admin's own budget is untouched.
    assert _upload(_client(second), "d.pdf").status_code == 202


def test_read_and_update_actions_are_not_throttled(upload_rate):
    upload_rate("1/min")
    admin = _admin()
    client = _client(admin)
    assert _upload(client, "one.pdf").status_code == 202

    listing = client.get("/api/v1/admin/documents/")
    assert listing.status_code == 200

    document = Document.objects.get(title="Regulation one.pdf")
    update = client.patch(
        f"/api/v1/admin/documents/{document.id}/",
        {"title": "Renamed"},
        format="json",
    )
    assert update.status_code == 200
