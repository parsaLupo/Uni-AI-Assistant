from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models import User
from apps.documents.models import DocumentStatus
from apps.documents.serializers import DocumentSerializer

TEST_PASSWORD = "Str0ng-Passw0rd!"

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 60 >>
stream
BT /F1 12 Tf 100 700 Td (Hello Persian world) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 65535 f 
0000000058 65535 f 
0000000115 65535 f 
0000000241 65535 f 
0000000355 65535 f 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
426
%%EOF
"""


class IngestionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.edu", password=TEST_PASSWORD, role="ADMIN")

    def test_upload_and_process_makes_document_active_and_searchable(self):
        from apps.documents.services import enqueue_document_processing

        f = SimpleUploadedFile("doc.pdf", MINIMAL_PDF, content_type="application/pdf")
        serializer = DocumentSerializer(
            data={
                "title": "Regulations",
                "document_type": "regulation",
                "file": f,
            },
            context={"request": type("R", (), {"user": self.admin})()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        doc = serializer.save()
        # enqueue runs eagerly in tests
        enqueue_document_processing(doc)
        doc.refresh_from_db()
        self.assertEqual(doc.status, DocumentStatus.INDEXED)
        self.assertGreater(doc.chunks.count(), 0)
        chunk = doc.chunks.first()
        self.assertTrue(chunk.embedding)
        self.assertEqual(chunk.embedding_dimension, 64)
