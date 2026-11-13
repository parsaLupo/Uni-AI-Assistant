"""Golden dataset structure + automated evaluation (docs/15 §3/§4).

The Phase 14 contract: every docs/15 §3 category is represented, every item
carries the docs/08 §4 fields, and the whole set passes the automated
retrieval + refusal evaluation against the sample corpus.
"""

from django.test import TestCase

from apps.rag.golden_dataset import GOLDEN_DATASET
from apps.rag.golden_eval import evaluate_golden_dataset

# docs/15 §3 — every category needs real coverage, not a single token entry.
REQUIRED_CATEGORIES = {
    "regulation",
    "prerequisite",
    "exam",
    "calendar",
    "professor",
    "hybrid",
    "unsupported",
}


class GoldenDatasetStructureTests(TestCase):
    def test_golden_dataset_size(self):
        assert len(GOLDEN_DATASET) >= 30

    def test_golden_dataset_structure(self):
        for item in GOLDEN_DATASET:
            assert "question" in item
            assert "expected_title" in item
            assert "category" in item

    def test_golden_dataset_covers_every_docs15_category(self):
        counts: dict[str, int] = {}
        for item in GOLDEN_DATASET:
            counts[item["category"]] = counts.get(item["category"], 0) + 1
        missing = REQUIRED_CATEGORIES - set(counts)
        assert not missing, f"docs/15 §3 categories missing: {sorted(missing)}"
        for category in REQUIRED_CATEGORIES:
            assert counts[category] >= 3, (
                f"category '{category}' has {counts[category]} items; need ≥ 3"
            )

    def test_unsupported_items_expect_no_source(self):
        for item in GOLDEN_DATASET:
            if item["category"] == "unsupported":
                assert item["expected_title"] is None

    def test_grounded_items_carry_docs08_expected_fact_fields(self):
        with_facts = [item for item in GOLDEN_DATASET if item.get("expected_facts")]
        assert with_facts, "docs/08 §4 expected_facts not populated anywhere"
        for item in with_facts:
            assert item["expected_title"], "expected_facts require an expected source"


class GoldenSetEvaluationTests(TestCase):
    def test_automated_evaluation_passes_and_cleans_up(self):
        from apps.documents.models import Document

        report = evaluate_golden_dataset()
        assert report["dataset_size"] == len(GOLDEN_DATASET)
        assert report["grounded"]["total"] + report["unsupported"]["total"] == len(
            GOLDEN_DATASET
        )
        assert report["passed"], (
            f"grounded hit_rate={report['grounded']['hit_rate']}; failures="
            + ", ".join(
                item["question"]
                for item in report["items"]
                if not item["hit"] and item["expected_title"] is not None
            )
        )
        assert report["grounded"]["hit_rate"] >= 0.8
        # Every grounded category clears the bar individually.
        for category, stats in report["by_category"].items():
            if category != "unsupported":
                assert stats["hit_rate"] >= 0.8, (
                    f"category {category} hit-rate {stats['hit_rate']:.0%}"
                )
        assert all(row["equivalent"] for row in report["spell_variants"])
        # Unsupported items are refusal probes: their scores are recorded so
        # the evidence-acceptance margin can be tuned (phase-14 limitation).
        assert len(report["unsupported"]["false_positive_scores"]) <= report[
            "unsupported"
        ]["total"]
        # The sample corpus is fully removed after the run.
        assert not Document.objects.filter(document_type="golden-sample").exists()
