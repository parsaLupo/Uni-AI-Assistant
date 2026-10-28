"""Document API tests."""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.documents.models import Document, DocumentStatus

TEST_PASSWORD = "Str0ng-Passw0rd!"

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 60 >>\nstream\nBT /F1 12 Tf 100 700 Td (Hello Persian world) Tj ET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 65535 f \n0000000058 65535 f \n0000000115 65535 f \n0000000241 65535 f \n0000000355 65535 f \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n426\n%%EOF"


def _user(role="ADMIN"):
    return User.objects.create_user(email=f"{role.lower()}@example.edu", password=TEST_PASSWORD, role=role)


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


class DocumentApiTests(TestCase):
    def setUp(self):
        self.admin = _user("ADMIN")
        self.student = _user("STUDENT")
        self.client_admin = _client(self.admin)
        self.client_student = _client(self.student)

    def _upload(self, client, **overrides):
        data = {
            "title": "Regulations",
            "document_type": "regulation",
            "academic_year": "1405-1406",
            "file": SimpleUploadedFile("doc.pdf", PDF_BYTES, content_type="application/pdf"),
        }
        data.update(overrides)
        return client.post("/api/v1/admin/documents/", data, format="multipart")

    def test_upload_valid_pdf(self):
        res = self._upload(self.client_admin)
        self.assertEqual(res.status_code, 202, res.data)
        self.assertEqual(res.data["title"], "Regulations")
        self.assertEqual(res.data["status"], DocumentStatus.UPLOADED)
        self.assertTrue(res.data["checksum"])

    def test_invalid_extension_rejected(self):
        f = SimpleUploadedFile("doc.txt", PDF_BYTES, content_type="application/pdf")
        res = self._upload(self.client_admin, file=f)
        self.assertEqual(res.status_code, 400)

    def test_wrong_mime_rejected(self):
        f = SimpleUploadedFile("doc.pdf", PDF_BYTES, content_type="text/plain")
        res = self._upload(self.client_admin, file=f)
        self.assertEqual(res.status_code, 400)

    def test_fake_pdf_rejected(self):
        f = SimpleUploadedFile("doc.pdf", b"not a pdf", content_type="application/pdf")
        res = self._upload(self.client_admin, file=f)
        self.assertEqual(res.status_code, 400)

    def test_oversized_rejected(self):
        big = b"%PDF" + b"x" * (11 * 1024 * 1024)
        f = SimpleUploadedFile("big.pdf", big, content_type="application/pdf")
        res = self._upload(self.client_admin, file=f)
        self.assertEqual(res.status_code, 400)

    def test_encrypted_rejected(self):
        data = b"%PDF-1.4\n/Encrypt\n%%EOF"
        f = SimpleUploadedFile("enc.pdf", data, content_type="application/pdf")
        res = self._upload(self.client_admin, file=f)
        self.assertEqual(res.status_code, 400)

    def test_non_admin_denied(self):
        res = self._upload(self.client_student)
        self.assertIn(res.status_code, (401, 403))

    def test_version_auto_increment(self):
        self._upload(self.client_admin)
        res = self._upload(self.client_admin)
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.data["version"], 2)

    def test_activate_supersedes_previous(self):
        r1 = self._upload(self.client_admin)
        r2 = self._upload(self.client_admin)
        id1 = r1.data["id"]
        id2 = r2.data["id"]
        # activate first, then second
        self.client_admin.post(f"/api/v1/admin/documents/{id1}/activate/")
        res = self.client_admin.post(f"/api/v1/admin/documents/{id2}/activate/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], DocumentStatus.ACTIVE)
        d1 = Document.objects.get(pk=id1)
        self.assertEqual(d1.status, DocumentStatus.SUPERSEDED)

    def test_retry_failed(self):
        r = self._upload(self.client_admin)
        did = r.data["id"]
        doc = Document.objects.get(pk=did)
        doc.status = DocumentStatus.FAILED
        doc.processing_error = "boom"
        doc.save()
        res = self.client_admin.post(f"/api/v1/admin/documents/{did}/retry/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], DocumentStatus.UPLOADED)
        self.assertEqual(res.data["processing_error"], "")

    def test_list_and_detail(self):
        r = self._upload(self.client_admin)
        did = r.data["id"]
        res = self.client_admin.get("/api/v1/admin/documents/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["count"] if "count" in res.data else len(res.data.get("results", res.data)), 1)
        res2 = self.client_admin.get(f"/api/v1/admin/documents/{did}/")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.data["id"], did)

    def test_patch_status(self):
        r = self._upload(self.client_admin)
        did = r.data["id"]
        res = self.client_admin.patch(f"/api/v1/admin/documents/{did}/", {"status": "INACTIVE"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "INACTIVE")

    def test_delete(self):
        r = self._upload(self.client_admin)
        did = r.data["id"]
        res = self.client_admin.delete(f"/api/v1/admin/documents/{did}/")
        self.assertEqual(res.status_code, 204)
