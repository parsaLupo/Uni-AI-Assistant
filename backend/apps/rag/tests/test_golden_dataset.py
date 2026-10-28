from apps.rag.golden_dataset import GOLDEN_DATASET


def test_golden_dataset_size():
    assert len(GOLDEN_DATASET) >= 20


def test_golden_dataset_structure():
    for item in GOLDEN_DATASET:
        assert "question" in item
        assert "expected_title" in item
        assert "category" in item
