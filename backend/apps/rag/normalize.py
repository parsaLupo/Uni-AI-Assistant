"""Persian text normalization for indexing and querying (Phase 08 / V-04)."""

from __future__ import annotations

import re
import unicodedata

# Arabic/Persian look-alike letters → canonical Persian forms.
_LETTER_MAP = str.maketrans(
    {
        "\u064a": "\u06cc",  # Arabic yeh -> Persian yeh
        "\u0643": "\u06a9",  # Arabic kaf -> Persian kaf
        "\u0629": "\u0647",  # teh marbuta -> heh
        "\u0624": "\u0648",  # waw with hamza -> waw
        "\u0626": "\u06cc",  # yeh with hamza -> yeh
        "\u0625": "\u0627",  # alef with hamza below -> alef
        "\u0623": "\u0627",  # alef with hamza above -> alef
        "\u0622": "\u0627",  # alef with madda -> alef (conservative)
    }
)

_DIGIT_MAP = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)

# Tatweel / kashida and zero-width characters we never want to keep.
_TATWEEL = "\u0640"
_ZWSP = "\u200b"
_ZWNJ = "\u200c"
_ZWJ = "\u200d"


def _collapse_zwnj(text: str) -> str:
    # Preserve a single meaningful ZWNJ; drop duplicates and stray adjacency.
    text = re.sub(r"\u200c{2,}", "\u200c", text)
    # ZWNJ glued to whitespace is meaningless; remove it.
    text = re.sub(r"\s\u200c", " ", text)
    text = re.sub(r"\u200c\s", " ", text)
    return text


def normalize_persian(text: str | None) -> str:
    """Return a normalized form of *text* suitable for indexing and querying.

    The function is idempotent and safe to call on already-normalized text.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.translate(_LETTER_MAP)
    text = text.translate(_DIGIT_MAP)
    text = text.replace(_TATWEEL, "")
    text = text.replace(_ZWSP, "")
    text = text.replace(_ZWJ, "")
    text = _collapse_zwnj(text)

    # Punctuation normalization: unify common Arabic/Persian punctuation.
    text = text.replace("،", "،").replace("؛", "؛")
    text = text.replace("\u201c", "«").replace("\u201d", "»")
    text = text.replace("\u2018", "«").replace("\u2019", "»")

    # Collapse whitespace while preserving paragraph breaks and ZWNJ.
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()
