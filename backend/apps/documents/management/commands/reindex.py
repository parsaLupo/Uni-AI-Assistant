"""Reindex documents."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.documents.models import Document
from apps.rag.ingestion import ingest_document


class Command(BaseCommand):
    help = "Reindex one or all documents."

    def add_arguments(self, parser):
        parser.add_argument("--document-id", type=int, default=None)
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        if options["all"]:
            documents = Document.objects.all()
        elif options["document_id"]:
            documents = Document.objects.filter(pk=options["document_id"])
        else:
            self.stderr.write("Specify --document-id or --all")
            return
        for document in documents:
            try:
                result = ingest_document(document.id)
                self.stdout.write(self.style.SUCCESS(f"reindexed {document.id}: {result}"))
            except Exception as exc:  # noqa: BLE001
                self.stderr.write(self.style.ERROR(f"failed {document.id}: {exc}"))
