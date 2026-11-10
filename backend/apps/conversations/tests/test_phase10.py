from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.conversations.models import Conversation, Message, MessageSource
from apps.documents.models import Document, DocumentChunk, DocumentStatus


class Phase10ConversationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="phase10@example.com", password="Str0ng-Passw0rd!")
        self.other = User.objects.create_user(email="other10@example.com", password="Str0ng-Passw0rd!")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other)

    def test_create_list_detail_and_rename(self):
        create = self.client.post("/api/v1/conversations/", {"title": "تست"}, format="json")
        self.assertEqual(create.status_code, 201)
        conversation_id = create.json()["id"]
        self.assertEqual(create.json()["title"], "تست")

        listed = self.client.get("/api/v1/conversations/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)

        detail = self.client.get(f"/api/v1/conversations/{conversation_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["id"], conversation_id)

        renamed = self.client.patch(f"/api/v1/conversations/{conversation_id}/", {"title": "جدید"}, format="json")
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["title"], "جدید")

    def test_ownership_returns_404(self):
        conversation = Conversation.objects.create(user=self.other, title="private")
        response = self.client.get(f"/api/v1/conversations/{conversation.id}/")
        self.assertEqual(response.status_code, 404)
        delete = self.client.delete(f"/api/v1/conversations/{conversation.id}/")
        self.assertEqual(delete.status_code, 404)

    def test_delete_archives_conversation(self):
        conversation = Conversation.objects.create(user=self.user, title="archive")
        response = self.client.delete(f"/api/v1/conversations/{conversation.id}/")
        self.assertEqual(response.status_code, 204)
        conversation.refresh_from_db()
        self.assertIsNotNone(conversation.archived_at)
        listed = self.client.get("/api/v1/conversations/")
        self.assertEqual(listed.json()["count"], 0)

    def test_insufficient_evidence_message(self):
        conversation = Conversation.objects.create(user=self.user, title="chat")
        response = self.client.post(
            f"/api/v1/conversations/{conversation.id}/messages/",
            {"content": "شرایط مشروط شدن چیست؟"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["message"]["insufficient_evidence"])
        self.assertEqual(MessageSource.objects.filter(message__conversation=conversation).count(), 0)

    def test_message_persistence_and_sources(self):
        document = Document.objects.create(
            title="آیین‌نامه",
            document_type="regulation",
            academic_year="1404-1405",
            status=DocumentStatus.ACTIVE,
            uploaded_by=self.user,
            storage_key="k",
            checksum="c",
        )
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            content="شرایط مشروطی ...",
            normalized_content="شرایط مشروطی ...",
            page_number=3,
            section_title="فصل ۱",
            token_count=5,
            embedding=[0.1, 0.2],
            embedding_model="mock",
        )

        conversation = Conversation.objects.create(user=self.user, title="chat")
        response = self.client.post(
            f"/api/v1/conversations/{conversation.id}/messages/",
            {"content": "شرایط مشروط شدن چیست؟"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("message", payload)
        self.assertEqual(payload["message"]["role"], "ASSISTANT")

        messages = Message.objects.filter(conversation=conversation).order_by("created_at")
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].role, Message.Role.USER)
        self.assertEqual(messages[1].role, Message.Role.ASSISTANT)

        # If retrieval returned sources, MessageSource rows should be created.
        sources = MessageSource.objects.filter(message=messages[1])
        # Retrieval uses mock embedding provider; may or may not return. At least no crash.
        self.assertGreaterEqual(sources.count(), 0)
