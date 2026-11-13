"""Retention behaviour for chat history (docs/14-data-lifecycle.md, OA-07).

Policy (Phase 15 decision): an archived conversation is hard-deleted
`RETENTION_CONVERSATION_DAYS` days after `archived_at`; messages and message
sources cascade. Unarchived conversations are never touched, documents are
retained as official records, and the command is a no-op without `--yes`.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO

from apps.conversations.models import Conversation, Message
from apps.documents.models import Document, DocumentStatus
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone


def _archived(user, days_ago: int) -> Conversation:
    conversation = Conversation.objects.create(user=user, title="t")
    conversation.archived_at = timezone.now() - timedelta(days=days_ago)
    conversation.save(update_fields=["archived_at"])
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content="old")
    return conversation


class ApplyRetentionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="retention@example.edu", password="Str0ng-Passw0rd!"
        )
        self.old_archived = _archived(user, days_ago=365)
        self.recent_archived = _archived(user, days_ago=10)
        self.live_old = _archived(user, days_ago=365)
        # The command only deletes archived conversations: this one is live.
        self.live_old.archived_at = None
        self.live_old.save(update_fields=["archived_at"])
        self.document = Document.objects.create(
            title="آیین‌نامه",
            document_type="regulation",
            status=DocumentStatus.ACTIVE,
            checksum="retained",
            storage_key="documents/retained.pdf",
        )

    def test_expired_archived_conversations_are_hard_deleted(self):
        call_command("apply_retention", yes=True)

        self.assertFalse(Conversation.objects.filter(pk=self.old_archived.pk).exists())
        self.assertFalse(
            Message.objects.filter(conversation_id=self.old_archived.pk).exists()
        )

    def test_recently_archived_and_live_conversations_are_kept(self):
        call_command("apply_retention", yes=True)

        self.assertTrue(Conversation.objects.filter(pk=self.recent_archived.pk).exists())
        self.assertTrue(Conversation.objects.filter(pk=self.live_old.pk).exists())

    def test_documents_are_retained(self):
        call_command("apply_retention", yes=True)

        self.assertTrue(Document.objects.filter(pk=self.document.pk).exists())

    def test_command_refuses_to_delete_without_confirmation(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("apply_retention")

        self.assertIn("--yes", str(ctx.exception))
        self.assertTrue(Conversation.objects.filter(pk=self.old_archived.pk).exists())

    def test_dry_run_reports_without_deleting(self):
        out = StringIO()
        call_command("apply_retention", dry_run=True, stdout=out)

        self.assertIn("conversations_to_delete=1", out.getvalue())
        self.assertTrue(Conversation.objects.filter(pk=self.old_archived.pk).exists())
        self.assertTrue(
            Message.objects.filter(conversation_id=self.old_archived.pk).exists()
        )
