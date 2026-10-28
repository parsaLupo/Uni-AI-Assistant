from apps.rag.chunking import chunk_pages, count_tokens


def test_chunk_pages_basic():
    pages = [{"page_number": 1, "text": "جمله اول. جمله دوم. " * 20, "supported": True}]
    chunks = chunk_pages(pages, target_tokens=10, overlap_tokens=2)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["page_number"] == 1
        assert chunk["token_count"] > 0
        assert "chunk_index" in chunk


def test_chunk_pages_skips_unsupported():
    pages = [{"page_number": 1, "text": "", "supported": False}]
    assert chunk_pages(pages) == []


def test_count_tokens():
    assert count_tokens("یک دو سه") == 3
    assert count_tokens("") == 0
