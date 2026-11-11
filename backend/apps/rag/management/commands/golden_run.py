"""`manage.py golden_run` — automated golden-set evaluation (docs/15 §4).

Builds the sample corpus of docs/08 §4, runs every golden item through the
retrieval service, and writes the report next to the phase docs. Repeatable:
the corpus is created and removed inside the run, and the command is guarded
to development exactly like `seed` (V-13) so no production database is ever
touched.

    python manage.py golden_run
    docker compose exec backend python manage.py golden_run
"""

from __future__ import annotations

import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.rag.golden_eval import evaluate_golden_dataset, save_report


class Command(BaseCommand):
    help = (
        "Run the RAG golden dataset (docs/15 §3/§4): retrieval + refusal per "
        "item, per-category hit-rate, spell-variant equivalence; writes "
        "university-assistant-docs/reports/golden-set-report.{json,md}."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--top-k", type=int, default=None, help="Override the top-k window."
        )
        parser.add_argument(
            "--threshold", type=float, default=None, help="Override the score threshold."
        )
        parser.add_argument(
            "--no-report",
            action="store_true",
            help="Do not write the report files (stdout only).",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "golden_run is development-only (like seed): refusing to run "
                "against a non-development database."
            )

        kwargs = {}
        if options["top_k"]:
            kwargs["top_k"] = options["top_k"]
        if options["threshold"]:
            kwargs["threshold"] = options["threshold"]
        report = evaluate_golden_dataset(**kwargs)

        self.stdout.write(
            f"dataset={report['dataset_size']} hits={report['hits']} "
            f"hit_rate={report['hit_rate']:.0%} "
            f"(required ≥ {report['required_hit_rate']:.0%})"
        )
        for category, stats in sorted(report["by_category"].items()):
            self.stdout.write(
                f"  {category:<14} {stats['hits']}/{stats['total']} "
                f"({stats['hit_rate']:.0%}) avg_score={stats['avg_score']}"
            )
        for row in report["spell_variants"]:
            mark = "✅" if row["equivalent"] else "❌"
            self.stdout.write(f"  variant {mark} {row['variant']} ≡ {row['base']}")

        if not options["no_report"]:
            json_path, md_path = save_report(report)
            self.stdout.write(f"report written: {json_path.name}, {md_path.name}")

        if not report["passed"]:
            self.stdout.write(self.style.ERROR("golden set FAILED — see report"))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("golden set PASS"))
