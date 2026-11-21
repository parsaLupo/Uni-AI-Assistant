"""Resolve a free-text course query (code or Persian title) to catalog rows.

The Course Selection Assistant accepts either a numeric course code or a
Persian course name. This module is the *only* place that maps the student's
input to a course; it never evaluates eligibility. ``CourseSelectionEngine``
still receives the resolved, real course code, so every rule and reason code is
unchanged.

Matching is deterministic and intentionally conservative (docs/17 "Insufficient
evidence"):

1. exact course code;
2. exact normalized title (the ``normalized_title`` column written by
   ``Course.save``);
3. unambiguous title containment with a minimum-length guard;
4. otherwise ``not_found`` — or, when more than one catalog row matches,
   ``ambiguous`` with the candidate list, so the student picks explicitly.

There is no fuzzy/distance matching: a title is never "probably" the requested
course, because a wrong silent match would evaluate eligibility for the wrong
course.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from apps.common.persian import normalize_persian
from apps.courses.models import Course

# A containment query shorter than this would match unrelated courses by
# accident («زبان» vs «زبان‌شناسی»…). Exact code/title matches are unaffected.
MIN_CONTAINMENT_LENGTH = 4
# Bound the ambiguity payload; the UI asks for a more specific name when the
# query is broader than this.
MAX_CANDIDATES = 20

MatchStatus = Literal["resolved", "ambiguous", "not_found"]

_CANDIDATE_QUERYSET = Course.objects.select_related("department")


@dataclass(frozen=True)
class CourseMatch:
    """Outcome of resolving one query. ``candidates`` is never auto-selected."""

    status: MatchStatus
    query: str
    course: Course | None = None
    candidates: list[Course] = field(default_factory=list)
    total: int = 0


def candidate_payload(course: Course) -> dict[str, Any]:
    """Distinguishing fields shown in the ambiguity picker (no eligibility)."""
    return {
        "code": course.code,
        "title": course.title,
        "credits": course.credits,
        "department": course.department.name if course.department_id else "",
        "course_type": course.course_type,
    }


def _ambiguous(query: str, queryset) -> CourseMatch:
    total = queryset.count()
    candidates = list(queryset.order_by("code")[:MAX_CANDIDATES])
    return CourseMatch("ambiguous", query, candidates=candidates, total=total)


def resolve_course(raw_query: str) -> CourseMatch:
    """Return the deterministic resolution of *raw_query* (code or title)."""
    query = str(raw_query or "").strip()
    normalized = normalize_persian(query)
    if not normalized:
        return CourseMatch("not_found", query)

    # 1. Exact course code. Normalizing first also accepts Persian/Arabic digits
    #    and stray spaces; the raw form is kept as a fallback for codes that
    #    contain characters the normalizer strips.
    code_match = (
        _CANDIDATE_QUERYSET.filter(code__iexact=normalized).first()
        or _CANDIDATE_QUERYSET.filter(code__iexact=query).first()
    )
    if code_match is not None:
        return CourseMatch("resolved", query, course=code_match)

    # 2. Exact normalized title (spaces/ZWNJ/yeh/kaf/digit variants collapse).
    exact = _CANDIDATE_QUERYSET.filter(normalized_title=normalized)
    if exact.count() == 1:
        return CourseMatch("resolved", query, course=exact.first())
    if exact.count() > 1:
        return _ambiguous(query, exact)

    # 3. Unambiguous containment ("نظریه زبان" inside the full catalog title).
    #    Only a single surviving row is resolved; two or more stay ambiguous.
    if len(normalized) >= MIN_CONTAINMENT_LENGTH:
        contained = _CANDIDATE_QUERYSET.filter(normalized_title__icontains=normalized)
        total = contained.count()
        if total == 1:
            return CourseMatch("resolved", query, course=contained.first())
        if total > 1:
            return _ambiguous(query, contained)

    # 4. No reliable match: the caller answers with an explicit not-found state.
    return CourseMatch("not_found", query)
