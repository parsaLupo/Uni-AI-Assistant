"""`manage.py seed` — populate a clean database from `data/*.json` (V-13).

Idempotent and deterministic; guarded to development settings so production
can never be seeded with demo identities (improvements.md I-13).
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.common.seed_data import Seeder


class Command(BaseCommand):
    help = (
        "Seed the database with the real MVP dataset (data/*.json): faculties, "
        "departments, courses + prerequisites, professors, terms, offerings "
        "(schedules/exams parsed from Persian strings), demo content and — in "
        "development — demo accounts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=None,
            help="Path to the data directory (default: <repo root>/data).",
        )
        parser.add_argument(
            "--no-demo-accounts",
            action="store_true",
            help="Skip demo login identities.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not settings.IS_TESTS:
            raise CommandError(
                "seed refuses to run outside development (DJANGO_DEBUG=true); "
                "demo data and credentials must never reach production."
            )
        data_dir = Path(options["data_dir"]) if options["data_dir"] else (
            Path(settings.BASE_DIR).parent / "data"
        )
        if not data_dir.is_dir():
            raise CommandError(f"data directory not found: {data_dir}")

        seeder = Seeder(data_dir, self.stdout)
        try:
            counts = seeder.run(with_demo_accounts=not options["no_demo_accounts"])
        except FileNotFoundError as exc:
            raise CommandError(str(exc)) from exc

        if counts:
            for key, value in counts.items():
                self.stdout.write(f"  {key}: +{value}")
        else:
            self.stdout.write("  already seeded — nothing to do (idempotent).")
        if seeder.credentials:
            self.stdout.write(self.style.SUCCESS("Demo accounts (development only):"))
            for line in seeder.credentials:
                self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS("Done."))
