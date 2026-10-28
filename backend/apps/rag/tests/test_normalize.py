from apps.rag.normalize import normalize_persian


def test_normalize_arabic_to_persian_letters():
    assert normalize_persian("ي") == "ی"
    assert normalize_persian("ك") == "ک"


def test_normalize_digits():
    assert normalize_persian("۱۲۳") == "123"
    assert normalize_persian("٤٥٦") == "456"


def test_normalize_zwnj_preserved_or_cleaned():
    result = normalize_persian("نیم\u200cفاصله")
    assert "نیم" in result
    assert "فاصله" in result


def test_normalize_idempotent():
    text = "سَلام دنیا ۱۲۳"
    once = normalize_persian(text)
    assert normalize_persian(once) == once


def test_normalize_variants_retrieve_same():
    a = normalize_persian("كیك ی")
    b = normalize_persian("کیک ی")
    assert a == b
