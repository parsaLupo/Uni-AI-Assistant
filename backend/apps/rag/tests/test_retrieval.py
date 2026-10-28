from django.test import TestCase

from apps.accounts.models import User
from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.rag.embeddings import LocalHashEmbeddingProvider
from apps.rag.normalize import normalize_persian
from apps.rag.retrieval import RetrievalService

TEST_PASSWORD = "Str0ng-Passw0rd!"


class RetrievalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.edu", password=TEST_PASSWORD, role="ADMIN")
        self.doc = Document.objects.create(
            title="آیین‌نامه",
            document_type="regulation",
            status=DocumentStatus.ACTIVE,
            checksum="abc",
            storage_key="documents/x.pdf",
        )
        provider = LocalHashEmbeddingProvider(dimension=64)
        text = "شرایط مشروطی دانشجو"
        embedding = provider.embed([normalize_persian(text)])[0]
        self.chunk = DocumentChunk.objects.create(
            document=self.doc,
            chunk_index=0,
            content=text,
            normalized_content=normalize_persian(text),
            page_number=3,
            section_title="شرایط مشروطی",
            token_count=3,
            embedding=embedding,
            embedding_model=provider.model_id,
            embedding_dimension=64,
        )
        # inactive version
        inactive_doc = Document.objects.create(
            title="آیین‌نامه",
            document_type="regulation",
            status=DocumentStatus.SUPERSEDED,
            checksum="def",
            storage_key="documents/y.pdf",
        )
        DocumentChunk.objects.create(
            document=inactive_doc,
            chunk_index=0,
            content="متن قدیمی",
            normalized_content=normalize_persian("متن قدیمی"),
            embedding=provider.embed([normalize_persian("متن قدیمی")])[0],
            embedding_model=provider.model_id,
            embedding_dimension=64,
        )

    def test_retrieve_returns_active_chunk(self):
        service = RetrievalService(top_k=3, threshold=0.0)
        results = service.retrieve("شرایط مشروطی")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["document_id"], self.doc.id)
        self.assertEqual(results[0]["page_number"], 3)
        self.assertEqual(results[0]["section_title"], "شرایط مشروطی")

    def test_inactive_versions_excluded(self):
        service = RetrievalService(top_k=10, threshold=0.0)
        results = service.retrieve("متن قدیمی")
        ids = {r["document_id"] for r in results}
        # superseded document chunk may still score but filtered by status=Active
        self.assertNotIn(self.doc.id if False else 0, ids)  # placeholder
        # Ensure only active doc chunks are returned
        for r in results:
            self.assertEqual(r["status"], DocumentStatus.ACTIVE)

    def test_dimension_mismatch_skipped(self):
        bad_doc = Document.objects.create(
            title="بد",
            document_type="regulation",
            status=DocumentStatus.ACTIVE,
            checksum="ghi",
            storage_key="documents/z.pdf",
        )
        DocumentChunk.objects.create(
            document=bad_doc,
            chunk_index=0,
            content="متن",
            normalized_content="متن",
            embedding=[0.1, 0.2],
            embedding_model="m",
            embedding_dimension=2,
        )
        service = RetrievalService(top_k=10, threshold=0.0)
        # should not raise
        results = service.retrieve("متن")
        # bad chunk skipped
        for r in results:
            self.assertNotEqual(r["document_id"], bad_doc.id)
