"""Golden-set evaluation harness (Phase 14, docs/15 §2–§4).

The Phase 08 seed defined 22 question/source pairs; Phase 14 expands the set
to cover every category in ``docs/15`` §3 and automates the run (docs/15 §4
regression rule: rerun whenever prompts, embeddings, chunking or retrieval
change).

Two deterministic, offline components:

* ``build_golden_corpus`` — creates the official-looking sample documents of
  docs/08 §4 as real ``Document``/``DocumentChunk`` rows (hash embeddings,
  page/section metadata), tagged ``document_type="golden-sample"`` so the
  evaluator can scope retrieval to exactly this corpus and the caller can
  clean up afterwards.
* ``evaluate_golden_dataset`` — retrieval quality per docs/15 §2 (source
  relevance, top-k usefulness, page/section alignment, language variants) and
  refusal behaviour for unsupported items. Returns a machine-readable report
  consumed by the ``golden_run`` management command, the pytest suite and the
  committed Markdown/JSON reports.

The corpus embeds with a 256-dimensional hash projection: at the Phase 08
64-dimension test setting, SHA-256 bucket collisions between unrelated tokens
produced false positives above the score threshold; 256 keeps the same
deterministic adapter while separating the corpus vocabulary.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from statistics import mean

from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.rag.embeddings import LocalHashEmbeddingProvider
from apps.rag.golden_dataset import GOLDEN_DATASET
from apps.rag.normalize import normalize_persian
from apps.rag.retrieval import RetrievalService

CORPUS_DOCUMENT_TYPE = "golden-sample"
CHECKSUM_PREFIX = "golden-sample-"
EMBEDDING_DIMENSION = 256

# docs/08 §4: a limited number of official-looking sample documents. Each
# chunk below is the source a docs/15 §3 category maps to, written with the
# terminology the golden questions use (terminology preservation, docs/15 §2).
SAMPLE_DOCUMENTS: dict[str, list[str]] = {
    "آیین‌نامه آموزشی": [
        "شرایط مشروطی دانشجو: در صورت کاهش معدل، دانشجو مشروط می‌شود و در ترم مشروط "
        "سقف واحد محدود است و حداقل واحد برای ترم مشروط طبق آیین‌نامه آموزشی تعیین می‌شود.",
        "نحوه انصراف از تحصیل و مرخصی تحصیلی و شرایط انتقالی و مهمان شدن در دانشگاه دیگر "
        "بر اساس آیین‌نامه آموزشی است.",
        "سقف واحد دانشجویان ترم اول، شرایط اخذ درس بدون پیش‌نیاز، نحوه محاسبه معدل ترم، "
        "حداقل نمره قبولی درس و نحوه اعتراض به نمره در آیین‌نامه آموزشی آمده است.",
        "انتخاب درس بر اساس دروس پاس‌شده و پیش‌نیازها و سقف واحد مندرج در آیین‌نامه آموزشی "
        "انجام می‌شود؛ پیش‌نیاز هر درس در سیلابس درس نیز آمده است.",
    ],
    "سیلابس درس": [
        "پیش‌نیاز درس کارگاه کامپیوتر درس پایه است؛ برای اخذ مبانی برنامه‌نویسی نیز "
        "پیش‌نیاز لازم است و پیش‌نیازهای هر درس در سیلابس درس ثبت می‌شود.",
    ],
    "تقویم آموزشی": [
        "مهلت حذف و اضافه، برگزاری کلاس‌های جبرانی و شروع کلاس‌ها بر اساس تقویم آموزشی "
        "اعلام می‌شود.",
    ],
    "برنامه امتحانات": [
        "تاریخ امتحان میان‌ترم و امتحان پایان‌ترم هر درس همراه با سالن برگزاری امتحان "
        "در برنامه امتحانات اعلام می‌شود.",
    ],
    "فهرست اساتید": [
        "استاد درس مبانی برنامه‌نویسی و استاد درس پایه و اعضای هیئت علمی گروه کامپیوتر "
        "در فهرست اساتید آمده است.",
    ],
    "راهنمای ثبت‌نام": [
        "نحوه ثبت‌نام در کارگاه‌ها و امکان تغییر گروه درسی در راهنمای ثبت‌نام توضیح داده می‌شود.",
    ],
    "آیین‌نامه بورسیه": [
        "شرایط بورسیه تحصیلی در آیین‌نامه بورسیه آمده است.",
    ],
    "راهنمای پایان‌نامه": [
        "مدارک لازم برای دفاع پایان‌نامه در راهنمای پایان‌نامه فهرست شده است.",
    ],
}

TOP_K = 3
THRESHOLD = 0.2
REQUIRED_HIT_RATE = 0.8  # docs/08 acceptance: ≥ 80% top-3 from Phase 08

def build_golden_corpus(
    provider: LocalHashEmbeddingProvider | None = None,
) -> list[Document]:
    """Create the sample documents; returns the rows (caller cleans up)."""
    provider = provider or LocalHashEmbeddingProvider(dimension=EMBEDDING_DIMENSION)
    documents: list[Document] = []
    for title_index, (title, contents) in enumerate(SAMPLE_DOCUMENTS.items()):
        document = Document.objects.create(
            title=title,
            document_type=CORPUS_DOCUMENT_TYPE,
            academic_year="1405-1406",
            effective_from=date.today(),
            status=DocumentStatus.ACTIVE,
            checksum=f"{CHECKSUM_PREFIX}{title_index:04d}",
            storage_key=f"documents/{CHECKSUM_PREFIX}{title_index:04d}.pdf",
        )
        for index, content in enumerate(contents):
            DocumentChunk.objects.create(
                document=document,
                chunk_index=index,
                content=content,
                normalized_content=normalize_persian(content),
                page_number=index + 1,
                section_title=normalize_persian(title),
                token_count=max(1, len(content.split())),
                embedding=provider.embed([normalize_persian(content)])[0],
                embedding_model=provider.model_id,
                embedding_dimension=provider.dimension,
            )
        documents.append(document)
    return documents


def delete_golden_corpus() -> int:
    count, _ = Document.objects.filter(document_type=CORPUS_DOCUMENT_TYPE).delete()
    return count


def evaluate_golden_dataset(
    top_k: int = TOP_K,
    threshold: float = THRESHOLD,
) -> dict:
    """Run every golden item; return the full evaluation report (docs/15 §2)."""
    provider = LocalHashEmbeddingProvider(dimension=EMBEDDING_DIMENSION)
    build_golden_corpus(provider)
    try:
        service = RetrievalService(provider=provider, top_k=top_k, threshold=threshold)
        rows: list[dict] = []
        for item in GOLDEN_DATASET:
            started = time.monotonic()
            results = service.retrieve(
                item["question"], filters={"document_type": CORPUS_DOCUMENT_TYPE}
            )
            titles = [result["title"] for result in results]
            expected = item["expected_title"]
            if expected is None:
                # Unsupported: the retrieval-level metric is refusal — the item
                # "hits" when the expected (nonexistent) source is absent, and
                # the recorded top score feeds the refusal-margin report.
                hit = len(results) == 0
                refused = len(results) == 0
                pages = []
            else:
                hit = expected in titles[:top_k]
                refused = None
                pages = [
                    result["page_number"]
                    for result in results
                    if result["title"] == expected
                ]
            rows.append(
                {
                    "question": item["question"],
                    "category": item["category"],
                    "expected_title": expected,
                    "retrieved": titles,
                    "retrieved_pages": pages,
                    "top_score": round(results[0]["score"], 4) if results else None,
                    "spell_variant": item.get("spell_variant"),
                    "hit": hit,
                    "refused": refused,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
            )

        # Language-variant equivalence: variant must hit the same source.
        base_by_question = {row["question"]: row for row in rows}
        variant_rows = []
        for item in GOLDEN_DATASET:
            variant = item.get("spell_variant")
            if not variant:
                continue
            variant_results = service.retrieve(
                variant, filters={"document_type": CORPUS_DOCUMENT_TYPE}
            )
            variant_titles = [result["title"] for result in variant_results]
            base_titles = base_by_question[item["question"]]["retrieved"]
            equivalent = bool(variant_titles) and variant_titles[:1] == base_titles[:1]
            variant_rows.append(
                {
                    "base": item["question"],
                    "variant": variant,
                    "base_top": base_titles[:1],
                    "variant_top": variant_titles[:1],
                    "equivalent": equivalent,
                }
            )

        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row["category"], []).append(row)
        by_category = {
            category: {
                "total": len(group),
                "hits": sum(1 for row in group if row["hit"]),
                "hit_rate": round(sum(1 for row in group if row["hit"]) / len(group), 4),
                "avg_score": round(
                    mean(
                        [
                            row["top_score"]
                            for row in group
                            if row["top_score"] is not None
                        ]
                    )
                    if any(row["top_score"] is not None for row in group)
                    else 0.0,
                    4,
                ),
            }
            for category, group in grouped.items()
        }

        # docs/08 gate: the ≥ 80% top-k rate applies to grounded questions.
        # Unsupported items measure refusal separately: their scores are
        # reported so the evidence-acceptance margin can be tuned (the answer
        # layer currently treats any non-empty retrieval as sufficient —
        # recorded as a Phase 15 hardening trigger in phase-14.md).
        grounded = [row for row in rows if row["expected_title"] is not None]
        unsupported = [row for row in rows if row["expected_title"] is None]
        grounded_hits = sum(1 for row in grounded if row["hit"])
        grounded_hit_rate = round(grounded_hits / len(grounded), 4)
        refusal_scores = sorted(
            [row["top_score"] for row in unsupported if row["top_score"] is not None],
            reverse=True,
        )
        hits = sum(1 for row in rows if row["hit"])
        return {
            "dataset_size": len(rows),
            "top_k": top_k,
            "threshold": threshold,
            "embedding_model": provider.model_id,
            "embedding_dimension": provider.dimension,
            "hits": hits,
            "hit_rate": round(hits / len(rows), 4),
            "grounded": {
                "total": len(grounded),
                "hits": grounded_hits,
                "hit_rate": grounded_hit_rate,
            },
            "unsupported": {
                "total": len(unsupported),
                "refused": sum(1 for row in unsupported if row["refused"]),
                "false_positive_scores": refusal_scores,
                "refusal_margin_note": (
                    "scores above the retrieval threshold on unsupported "
                    "questions must stay below the answer layer's future "
                    "evidence-acceptance margin (docs/15 §2 refusal)"
                ),
            },
            "required_hit_rate": REQUIRED_HIT_RATE,
            "passed": grounded_hit_rate >= REQUIRED_HIT_RATE
            and all(row["equivalent"] for row in variant_rows),
            "by_category": by_category,
            "spell_variants": variant_rows,
            "items": rows,
        }
    finally:
        delete_golden_corpus()


def report_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[3] / "university-assistant-docs" / "reports"
    return root / "golden-set-report.json", root / "golden-set-report.md"


def save_report(report: dict) -> tuple[Path, Path]:
    """Persist the report next to the phase docs (exit evidence)."""
    json_path, md_path = report_paths()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# Golden-set report (Phase 14)",
        "",
        f"* dataset: {report['dataset_size']} items — top-{report['top_k']}, "
        f"threshold {report['threshold']}",
        f"* embedding: `{report['embedding_model']}` (dim {report['embedding_dimension']})",
        f"* grounded top-{report['top_k']} hit-rate: **{report['grounded']['hit_rate']:.0%}** "
        f"({report['grounded']['hits']}/{report['grounded']['total']}; "
        f"required ≥ {report['required_hit_rate']:.0%}) — "
        f"{'PASS' if report['passed'] else 'FAIL'}",
        f"* unsupported refusal: "
        f"{report['unsupported']['refused']}/{report['unsupported']['total']} "
        f"refused outright; false-positive top scores above threshold: "
        f"{report['unsupported']['false_positive_scores'] or 'none'}",
        "",
        "| category | total | hits | hit-rate | avg score |",
        "|---|---|---|---|---|",
    ]
    for category, stats in sorted(report["by_category"].items()):
        lines.append(
            f"| {category} | {stats['total']} | {stats['hits']} | "
            f"{stats['hit_rate']:.0%} | {stats['avg_score']} |"
        )
    lines += ["", "## Spell-variant equivalence (ی/ي، ک/ك، نیم‌فاصله)", ""]
    for row in report["spell_variants"]:
        lines.append(
            f"* {'✅' if row['equivalent'] else '❌'} `{row['variant']}` ≡ `{row['base']}`"
        )
    lines += [
        "",
        "## Per-item results",
        "",
        "| question | category | expected | retrieved | hit |",
        "|---|---|---|---|---|",
    ]
    for row in report["items"]:
        lines.append(
            f"| {row['question']} | {row['category']} | "
            f"{row['expected_title'] or '(رفت/ناموجود)'} | "
            f"{', '.join(row['retrieved']) or '—'} | {'✅' if row['hit'] else '❌'} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
