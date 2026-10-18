"""Persian text normalization for search (architecture.md C-05).

"Normalize once, store twice, search with trigrams." The same function serves
`?search=` filtering now and RAG retrieval later, so search and retrieval can
never disagree ("the document exists but the assistant says it does not").

Rules (architecture.md section 4.4):
* Arabic yeh/kaf variants -> Persian yeh/kaf (ی/ي -> ی, ک/ك -> ک).
* Heh variants -> plain heh (ۀ/ة -> ه); tatweel (ـ) stripped.
* Arabic-Indic and Persian digits -> ASCII digits.
* ZWNJ (نیم‌فاصله) removed together with all whitespace, so «علوم کامپیوتر»,
  «علوم‌کامپیوتر» and «علومكامپيوتر» collapse to one index form.
* Common punctuation stripped so it can never split a trigram match.

The normalized form is stored in `normalized_*` columns at save time and the
query input is passed through this same function before matching — never
computed per request on the stored side.
"""

from __future__ import annotations

from django.db.models import Q

_YEH = str.maketrans({"ي": "ی", "ى": "ی", "ی": "ی"})
_KAF = str.maketrans({"ك": "ک", "ک": "ک"})
# Arabic combining marks (fatha/damma/kasra/tanween, hamza above, …): they
# carry no search meaning — «مبانِ» and «کرهٔ» must match their plain forms.
_MARKS = {0x064B + i for i in range(11)} | {0x0670} | set(range(0x06D6, 0x06EE))
_HEH = {"ه": "ه", "ۀ": "ه", "ة": "ه", "هَ": "ه", "هُ": "ه", "هِ": "ه"}
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# Characters removed entirely (tatweel, ZWNJ, whitespace, common punctuation).
_STRIP_CHARS = "ـ‎‏‪-‮ ­‐-―‌‍" \
    " \t\r\n" \
    "،,؛;؟?!.:«»\"'()[]{}-–—…ـ"


def normalize_persian(text: str | None) -> str:
    """Return the canonical index form of *text* (C-05). Never returns None."""
    if not text:
        return ""
    out = str(text).translate(_YEH).translate(_KAF).translate(_DIGITS)
    out = "".join(_HEH.get(ch, ch) for ch in out)
    out = "".join(
        ch for ch in out if ch not in _STRIP_CHARS and ord(ch) not in _MARKS
    )
    return out.casefold()


def normalized_search(queryset, search_value: str | None, *normalized_fields: str):
    """Filter *queryset* by *search_value* against the given normalized columns.

    The input is normalized with the same function that produced the stored
    columns, so variant spellings match on any engine; on PostgreSQL the
    `gin_trgm_ops` index over these columns accelerates the pattern scan.
    """
    value = normalize_persian(search_value)
    if not value or not normalized_fields:
        return queryset
    condition = Q()
    for field in normalized_fields:
        condition |= Q(**{f"{field}__icontains": value})
    return queryset.filter(condition)
