"""OA-07 retention: hard-delete archived conversations past the cutoff.

`docs/14-data-lifecycle.md` (Phase 15 decision): chat history is personal
data, so an archived conversation is hard-deleted
`RETENTION_CONVERSATION_DAYS` days after `archived_at`. Messages and message
sources cascade (FKs use `on_delete=CASCADE`). Documents are official
university records and are intentionally retained; audit logs are append-only
and have no application-level deletion path.

The command is cron-safe: it takes no DEBUG shortcuts, but it refuses to
delete anything without an explicit `--yes` (or `--dry-run`, which deletes
nothing). Run it as a daily scheduled job in production.
"""

from __future__ import annotations

from datetime import timedelta

from apps.conversations.models import Conversation
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Apply the conversation retention policy: hard-delete conversations "
        f"archived more than RETENTION_CONVERSATION_DAYS "
        f"(={settings.RETENTION_CONVERSATION_DAYS}) days ago."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm deletion. Without it the command refuses to run.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        days = int(settings.RETENTION_CONVERSATION_DAYS)
        if days <= 0:
            raise CommandError(
                "RETENTION_CONVERSATION_DAYS must be a positive number of days."
            )

        cutoff = timezone.now() - timedelta(days=days)
        doomed = Conversation.objects.filter(archived_at__lt=cutoff)
        count = doomed.count()

        if options["dry_run"]:
            self.stdout.write(
                f"dry_run=1 conversations_to_delete={count} cutoff={cutoff.isoformat()}"
            )
            return

        if not options["yes"]:
            raise CommandError(
                "Refusing to delete. Pass --yes to apply retention, or "
                "--dry-run to only report the affected conversations."
            )

        deleted, _ = doomed.delete()
        self.stdout.write(
            f"retention_applied deleted_conversations={count} "
            f"cutoff={cutoff.isoformat()}"
        )
