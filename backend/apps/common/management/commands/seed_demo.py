"""`manage.py seed_demo` — reproducible local demo data (Phase 16).

The normal `seed` command is development-only and prints the fixed demo
password. A release/local-demo stack runs with DEBUG=false, so it needs an
explicit, separately-guarded way to load the real academic dataset and the
demo identities without turning seeding into a production default.

Guards:
* ``DEMO_MODE=true`` must be set deliberately (see .env.example);
* ``DEMO_PASSWORD`` must be a unique local value of at least 10 characters;
* only the four reserved ``@semnan.local`` demo users are created/reset;
* every row is created with get_or_create, so re-running is a no-op.

The command never prints the password; read it from the local .env file or run
`scripts/show-demo-credentials.ps1` on the host.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.common.seed_data import Seeder

PLACEHOLDER_PASSWORDS = {"__change_me__", "change-me", "changeme", "demo", "password"}

# The password literal that used to ship in seed_data.py and docs. It is public
# (it appeared in Git history and READMEs), so it must never be accepted again.
PUBLIC_DEMO_PASSWORD_PATTERN = re.compile(r"demo[-_ ]?passw(?:or|0r)?d", re.IGNORECASE)


class Command(BaseCommand):
    help = (
        "Load the real academic dataset plus reproducible demo accounts and "
        "history for the local release demo (explicit DEMO_MODE only)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=None,
            help="Path to the data directory (default: <repo root>/data or /data).",
        )
        parser.add_argument(
            "--keep-passwords",
            action="store_true",
            help="Do not rotate the reserved demo accounts' passwords.",
        )
        parser.add_argument(
            "--skip-history",
            action="store_true",
            help="Skip demo passed courses and the welcome notification.",
        )

    def handle(self, *args, **options):
        if os.environ.get("DEMO_MODE", "").strip().lower() not in {"1", "true", "yes", "on"}:
            raise CommandError(
                "seed_demo requires DEMO_MODE=true. This command is for the local "
                "demo stack only; the normal release seed workflow never creates "
                "demo identities."
            )

        demo_password = os.environ.get("DEMO_PASSWORD", "").strip()
        if (
            len(demo_password) < 10
            or demo_password.lower() in PLACEHOLDER_PASSWORDS
            or PUBLIC_DEMO_PASSWORD_PATTERN.search(demo_password)
        ):
            raise CommandError(
                "DEMO_PASSWORD must be a unique local value of at least 10 "
                "characters and must not reuse the old public demo password. "
                "Generate one with scripts/init-env.ps1."
            )

        data_dir = (
            Path(options["data_dir"])
            if options["data_dir"]
            else Path(settings.BASE_DIR).parent / "data"
        )
        if not data_dir.is_dir():
            raise CommandError(f"data directory not found: {data_dir}")

        seeder = Seeder(data_dir, self.stdout)
        try:
            counts = seeder.run(
                with_demo_accounts=True,
                demo_password=demo_password,
                allow_demo_in_release=True,
                reset_demo_passwords=not options["keep_passwords"],
                demo_history=not options["skip_history"],
                reveal_demo_password=False,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        if counts:
            for key, value in counts.items():
                self.stdout.write(f"  {key}: +{value}")
        else:
            self.stdout.write("  demo data already present — nothing to do (idempotent).")

        self.stdout.write(self.style.SUCCESS("\nDemo accounts (local only, no password printed):"))
        for line in seeder.credentials:
            self.stdout.write(line)
        self.stdout.write(
            "\nThe password is DEMO_PASSWORD in your local .env. "
            "Run scripts/show-demo-credentials.ps1 on the host to print the full "
            "local credentials, and never commit or share that output."
        )
        self.stdout.write(self.style.SUCCESS("Done."))
