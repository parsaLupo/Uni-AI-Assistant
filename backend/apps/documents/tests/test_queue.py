"""Queue/enqueue tests."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.documents.models import Document, DocumentStatus
from apps.documents.services import enqueue_document_processing

TEST_PASSWORD = "Str0ng-Passw0rd!"


def _user(role="ADMIN"):
    return User.objects.create_user(email=f"{role.lower()}q@example.edu", password=TEST_PASSWORD, role=role)


class EnqueueTests(TestCase):
    def test_upload_enqueues_processing(self):
        admin = _user("ADMIN")
        from rest_framework.test import APIClient

        c = APIClient()
        c.force_authenticate(user=admin)
        pdf = b"%PDF-1.4\n%%EOF"
        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile("doc.pdf", pdf, content_type="application/pdf")
        with patch("apps.documents.views.enqueue_document_processing") as mock_enqueue:
            res = c.post(
                "/api/v1/admin/documents/",
                {"title": "T", "document_type": "regulation", "academic_year": "1405", "file": f},
                format="multipart",
            )
            self.assertEqual(res.status_code, 202)
            mock_enqueue.assert_called_once()
            self.assertIn("status_url", res.data)
            self.assertTrue(res.get("Location"))

    def test_retry_enqueues(self):
        admin = _user("ADMIN")
        doc = Document.objects.create(title="T", status=DocumentStatus.FAILED, processing_error="boom")
        with patch("apps.documents.views.enqueue_document_processing") as mock_enqueue:
            from rest_framework.test import APIClient

            c = APIClient()
            c.force_authenticate(user=admin)
            res = c.post(f"/api/v1/admin/documents/{doc.id}/retry/")
            self.assertEqual(res.status_code, 200)
            mock_enqueue.assert_called_once()
