"""Phase 14 — failure-mode tests (docs/08 §6 gates, checklist phase 14).

Each test provokes a failure the system must survive with a documented,
machine-readable envelope instead of a stack trace:

* expired access token           → 401 AUTHENTICATION_REQUIRED
* provider rate limit (HTTP 429) → 503 AI_PROVIDER_ERROR (Persian, no details)
* database down                  → 503 degraded health (no driver error text)
* concurrent edit (unique race)  → 409 CONFLICT via the DB backstop branch
* malformed request body         → 400 validation envelope
* failed document processing     → FAILED + retryable (Phase 07 loop)

Already covered elsewhere and referenced from phase-14.md, not duplicated:
provider timeout/outage/malformed output (apps/ai/tests/test_phase09.py),
malformed/oversized/encrypted uploads (apps/documents/tests/test_api.py),
refresh reuse/rotation (apps/accounts/tests/test_auth.py).
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.ai.providers import MockLLMProvider, ProviderError
from apps.courses.models import CourseOffering
from apps.documents.models import Document, DocumentStatus
from apps.documents.serializers import DocumentSerializer
from apps.students.models import Enrollment

pytestmark = pytest.mark.django_db

ME = "/api/v1/auth/me/"
ASK = "/api/v1/ai/ask/"
HEALTH = "/api/v1/health/"
PLANNER = "/api/v1/students/planner/"

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"


@pytest.fixture
def offering(academic_graph):
    return CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )


class TestExpiredAccessToken:
    def test_expired_access_token_is_a_401_envelope(self, api_client, student):
        token = AccessToken.for_user(student)
        # Re-sign the same token with a past expiry: signature valid, exp gone.
        token.payload["exp"] = int((timezone.now() - timedelta(seconds=1)).timestamp())
        response = api_client.get(ME, HTTP_AUTHORIZATION=f"Bearer {token}")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


class TestProviderRateLimit:
    def test_groq_429_is_categorized_rate_limit_and_retryable(self):
        from apps.ai.providers import GroqLLMProvider

        provider = GroqLLMProvider(api_key="k", model_id="m", timeout=1, max_retries=0)
        assert provider._categorize_http_status(429) == "rate_limit"
        assert provider._retryable("rate_limit")

    def test_rate_limited_provider_yields_503_ai_provider_error(self, authed_client, student):
        failing = MockLLMProvider(
            fail_with=ProviderError("rate_limit", "HTTP 429: too many requests")
        )
        with patch("apps.ai.views.build_llm_provider_from_env", return_value=failing):
            # "چیست" without any university keyword routes GENERAL, which
            # always reaches the provider; RAG questions may refuse before
            # ever calling it.
            response = authed_client(student).post(
                ASK, {"question": "عدد پی چیست؟"}, format="json"
            )
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "AI_PROVIDER_ERROR"
        # Persian, non-internal message: no "429", no English exception text.
        assert "429" not in body["error"]["message"]
        assert "too many requests" not in body["error"]["message"]


class TestDatabaseDown:
    def test_health_degrades_to_503_when_the_database_is_unreachable(self, api_client):
        with patch("apps.common.views.connections") as connections:
            connections["default"].ensure_connection.side_effect = RuntimeError("boom")
            response = api_client.get(HEALTH)
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        # The driver error stays in the logs, never in the body.
        assert "boom" not in response.content.decode()
        assert body["error"]["details"]["checks"]["database"] != "ok"


class TestConcurrentEdit:
    def test_concurrent_planner_add_hits_the_unique_backstop_with_a_409(
        self, authed_client, student, student_profile, offering
    ):
        """Two racing inserts: the exists() guard passes for both, the DB
        unique (student, offering) constraint catches the loser → 409."""
        with (
            patch.object(
                Enrollment.objects, "filter", return_value=Enrollment.objects.none()
            ),
            patch.object(
                Enrollment.objects, "create", side_effect=IntegrityError("unique race")
            ),
        ):
            response = authed_client(student).post(
                PLANNER, {"course_offering_id": offering.pk}, format="json"
            )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

    def test_duplicate_student_number_surfaces_a_409_not_a_500(
        self, authed_client, student, student_profile, academic_graph
    ):
        """Another flavour of the same race: the unique student_number decided
        by the database, not the serializer."""
        from apps.accounts.models import User

        rival = User.objects.create_user(email="rival@example.edu", password="x")
        from apps.students.models import StudentProfile

        StudentProfile.objects.create(
            user=rival, student_number="40412345", department=academic_graph["department"]
        )
        response = authed_client(student).patch(
            "/api/v1/students/me/",
            {
                "student_number": "40412345",
                "department_id": academic_graph["department"].pk,
            },
            format="json",
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"


class TestMalformedRequest:
    def test_malformed_json_body_is_a_400_envelope_not_a_500(self, api_client):
        response = api_client.post(
            "/api/v1/auth/login/",
            data='{"email": broken',
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] in ("VALIDATION_ERROR", "PARSE_ERROR")

    def test_empty_body_on_ai_ask_is_validation_error(self, authed_client, student):
        response = authed_client(student).post(ASK, {}, format="json")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


class TestProcessingFailureRecovery:
    def test_failed_document_is_marked_failed_and_retryable(self, admin):
        """End-to-end failure loop: upload → forced processing failure →
        FAILED with a stored reason → retry re-enqueues without re-upload."""
        from apps.documents.services import enqueue_document_processing

        upload = DocumentSerializer(
            data={
                "title": "سند شکست فاز ۱۴",
                "document_type": "regulation",
                "file": SimpleUploadedFile("broken.pdf", MINIMAL_PDF, "application/pdf"),
            },
            context={"request": type("R", (), {"user": admin})()},
        )
        assert upload.is_valid(), upload.errors
        doc = upload.save()

        # ADR-011 dev mode runs the task eagerly; attempt 1 < 3 makes the task
        # raise Celery's Retry after marking the row FAILED — accept either.
        from celery.exceptions import Retry as CeleryRetry

        with (
            patch(
                "apps.documents.tasks.ingest_document",
                side_effect=RuntimeError("extract exploded"),
            ),
            pytest.raises((CeleryRetry, RuntimeError)),
        ):
            enqueue_document_processing(doc)  # eager in tests (ADR-011 dev mode)
        doc.refresh_from_db()
        assert doc.status == DocumentStatus.FAILED
        assert doc.processing_error  # human-readable reason for the admin API
        assert doc.attempt_count == 1

        # Retry re-enqueues; the API never re-uploads.
        with patch("apps.documents.views.enqueue_document_processing") as mock_enqueue:
            from rest_framework.test import APIClient

            client = APIClient()
            client.force_authenticate(user=admin)
            response = client.post(f"/api/v1/admin/documents/{doc.id}/retry/")
        assert response.status_code == 200
        mock_enqueue.assert_called_once()
