"""C-05 normalizer tests — the character variants docs/11 calls out."""

from apps.common.persian import normalize_persian


def test_arabic_variants_collapse_to_persian():
    assert normalize_persian("كتاب") == normalize_persian("کتاب")  # Arabic kaf
    assert normalize_persian("علوم كامپيوتر") == normalize_persian("علوم کامپیوتر")
    assert normalize_persian("ماني") == normalize_persian("مانی")  # Arabic yeh


def test_heh_variants_and_tatweel():
    assert normalize_persian("کرهٔ") == normalize_persian("کره")
    assert normalize_persian("عـــلم") == normalize_persian("علم")


def test_digits_normalize_to_ascii():
    assert normalize_persian("۱۴۰۵") == "1405"
    assert normalize_persian("١٤٠٥") == "1405"


def test_zwnj_and_spacing_are_irrelevant_for_search():
    assert normalize_persian("علوم کامپیوتر") == normalize_persian("علوم‌کامپیوتر")
    assert normalize_persian("علوم کامپیوتر") == normalize_persian("علومکامپیوتر")


def test_punctuation_and_case_stripped():
    assert normalize_persian("«مبانیِ» فیزیک!") == normalize_persian("مبانی فیزیک")
    assert normalize_persian("API") == "api"


def test_none_and_empty():
    assert normalize_persian(None) == ""
    assert normalize_persian("") == ""
