"""Course-name resolution against the course catalog (root-cause fix).

Previous behaviour: questions such as
«پیش‌نیاز درس نظریه زبان‌ها و ماشین‌ها چیست؟» or
«پیش نیاز درس سیستم عامل چیست؟»
were answered with "insufficient evidence" or "please provide the course
code" because the old matcher

* clipped the question with a hand-maintained stop-word list (words like
  «چیست» and «پیشنیاز» were missing, so question words leaked into the
  compared title),
* compared against ``normalized_title`` which strips ALL whitespace, so the
  word-based branch silently compared one glued token per title, and
* flagged ANY duplicated catalog title as ambiguous, even though real
  database signals discriminate the rows (the catalog legitimately keeps
  one row per curriculum version of a course, e.g. 1916008 / 1916228 /
  1916354 for «نظریه زبان‌ها و ماشین‌ها»).

This module replaces that with a deterministic, data-driven resolver:

1. Course-code lookup (exact; never fuzzy).
2. Containment match: the full compact title must occur inside the compact
   question — question words stop mattering entirely.
3. Word-level similarity (only when no containment hit): every meaningful
   word of the title must appear among the question's words (fuzzy word
   similarity), tolerating ZWNJ vs space, ي/ی and ك/ك variants, Persian and
   Arabic digits, and minor spelling differences.
4. Context ranking with actual database records: the asking student's
   department/faculty, how central the course is in the prerequisite graph
   (its "curriculum footprint" — the per-curriculum-system detail is
   collapsed into CoursePrerequisite rows by seeding, so the graph is the
   best curriculum proxy available), whether the course is offered, and
   its core/elective type. Nested mentions («سیستم عامل» inside
   «آزمایشگاه سیستم عامل») are demoted in favour of the fuller phrase the
   user actually typed.
5. Ambiguity: the caller asks the user to disambiguate ONLY when two
   candidates are genuinely indistinguishable (scores within
   AMBIGUITY_MARGIN) — never merely because several rows share a name.
   No course, code or prerequisite is ever invented: when no reliable
   candidate exists the resolver returns an empty match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from apps.common.persian import normalize_persian
from apps.courses.models import Course, CourseOffering, CoursePrerequisite
from apps.students.models import StudentProfile

_SPLIT_RE = re.compile(r"[\s\u200c]+")
_CODE_PART_RE = re.compile(r"[_/]+")

# Words that carry no course-name meaning; dropped from token scoring so
# «زبان ها» (space) and «زبان‌ها» (ZWNJ) yield the same word set.
_FILLER_TOKENS = frozenset({"ها", "های", "و", "می", "تر", "ترین", "هاي"})
_MIN_TOKEN_LEN = 3
_MIN_TITLE_LEN = 3

# A title token, more informative than substring equality on compact forms.
_COVERAGE_MIN = 0.8          # ≥80% of the title's words must be found
_TOKEN_SIMILARITY_MIN = 0.75  # per-word similarity floor
_MIN_FUZZY_CHARS = 5          # guard against tiny accidental matches

# Context bonuses (real database signals, not question-text guesses).
_DEPARTMENT_BONUS = 0.2       # candidate belongs to the student's major
_FACULTY_BONUS = 0.1          # candidate belongs to the student's faculty
_CORE_TYPE_BONUS = 0.1        # core/compulsory beats elective/specialized
_OFFERED_BONUS = 0.05         # has at least one offering row
_GRAPH_BONUS_PER_EDGE = 0.04  # per distinct prerequisite-graph edge
_GRAPH_BONUS_CAP = 8          # cap on counted edges (0.32 max)

# «سیستم عامل» typed inside «آزمایشگاه سیستم عامل»-style questions: the
# fuller phrase the user typed wins.
_NESTED_PENALTY = 0.5

# Top candidate must beat the runner-up by this margin; smaller differences
# are treated as genuine ambiguity and surface a clarification instead of a
# course code demand.
_AMBIGUITY_MARGIN = 0.03

_CORE_TYPES = frozenset(
    normalize_persian(value)
    for value in ("اصلی", "الزامی", "اجباری", "پایه", "پایه ای")
)

_RATIO_CACHE: dict[tuple[str, str], float] = {}


@dataclass
class CourseMatch:
    """Result of course-name resolution with ambiguity information."""

    course: Course | None
    matches: list[Course]
    ambiguous: bool


@dataclass
class _Candidate:
    course: Course
    title_compact: str
    tokens: tuple[str, ...]
    text_score: float
    context_score: float = field(default=0.0)

    @property
    def score(self) -> float:
        return self.text_score + self.context_score


def _tokens(text: str) -> tuple[str, ...]:
    """Split on whitespace AND ZWNJ, normalizing each word independently."""
    return tuple(
        t for t in (normalize_persian(chunk) for chunk in _SPLIT_RE.split(text or ""))
        if t
    )


def _meaningful_tokens(text: str) -> tuple[str, ...]:
    """Course-name words only: length ≥3, filler plural/conjunction dropped."""
    return tuple(
        t
        for t in _tokens(text)
        if len(t) >= _MIN_TOKEN_LEN and t not in _FILLER_TOKENS
    )


def _word_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    pair = (a, b) if a <= b else (b, a)
    cached = _RATIO_CACHE.get(pair)
    if cached is None:
        cached = SequenceMatcher(None, a, b).ratio()
        _RATIO_CACHE[pair] = cached
    return cached


def _title_token_coverage(
    title_tokens: tuple[str, ...], question_tokens: tuple[str, ...], question_set: set[str]
) -> tuple[float, int]:
    """Char-weighted fraction of the title's words found in the question.

    A word counts when it occurs exactly or with ≥ _TOKEN_SIMILARITY_MIN
    similarity to any question word (handles small typos and suffix
    variants such as «زبان» vs «زبانها»).
    """
    covered = 0
    for token in title_tokens:
        if token in question_set:
            covered += len(token)
            continue
        best = max(_word_similarity(token, q) for q in question_tokens)
        if best >= _TOKEN_SIMILARITY_MIN:
            covered += len(token) * best
    return covered, sum(len(token) for token in title_tokens)


def _match_course_code(question: str) -> Course | None:
    """Exact code lookup; section suffixes like «1916001_02» are tolerated."""
    for raw in _SPLIT_RE.split(question or ""):
        for part in _CODE_PART_RE.split(raw or ""):
            token_norm = normalize_persian(part)
            if len(token_norm) >= 3 and any(ch.isdigit() for ch in token_norm):
                found = Course.objects.filter(code__iexact=token_norm).first()
                if found is not None:
                    return found
    return None


def _prerequisite_degrees() -> dict[int, tuple[int, int]]:
    """Distinct out/in prerequisite-graph edges per course id."""
    rows = set(
        CoursePrerequisite.objects.values_list("course_id", "prerequisite_course_id")
    )
    out_degrees: dict[int, int] = {}
    in_degrees: dict[int, int] = {}
    for course_id, prereq_id in rows:
        out_degrees[course_id] = out_degrees.get(course_id, 0) + 1
        in_degrees[prereq_id] = in_degrees.get(prereq_id, 0) + 1
    return {
        course_id: (out_degrees.get(course_id, 0), in_degrees.get(course_id, 0))
        for course_id in out_degrees.keys() | in_degrees.keys()
    }


def _collect_candidates(
    courses: list[Course], question_compact: str, question_tokens: tuple[str, ...]
) -> list[_Candidate]:
    question_set = set(question_tokens)
    containment: list[_Candidate] = []
    token_match: list[_Candidate] = []
    for course in courses:
        title_compact = normalize_persian(course.title)
        if not title_compact or len(title_compact) < _MIN_TITLE_LEN:
            continue
        tokens = _meaningful_tokens(course.title)
        if title_compact in question_compact:
            containment.append(
                _Candidate(course, title_compact, tokens, text_score=1.0)
            )
            continue
        if not tokens or not question_tokens:
            continue
        covered, total = _title_token_coverage(tokens, question_tokens, question_set)
        if total and covered >= _MIN_FUZZY_CHARS and covered / total >= _COVERAGE_MIN:
            token_match.append(
                _Candidate(course, title_compact, tokens, text_score=min(1.0, covered / total))
            )
    # Both paths contribute: a verbatim mention (containment) and an exact
    # word-level mention (every title word appears in the question) are the
    # same evidence at full strength, and merging them keeps spelled-out
    # variants («سیستم های عامل پیشرفته») that only one path can reach.
    candidates: dict[int, _Candidate] = {}
    for candidate in containment + token_match:
        existing = candidates.get(candidate.course.pk)
        if existing is None:
            candidates[candidate.course.pk] = candidate
        else:
            existing.text_score = max(existing.text_score, candidate.text_score)
    return list(candidates.values())


def _needs_context_bonus(profile: StudentProfile | None, candidate: _Candidate) -> float:
    """Student context only; scored separately from catalog-owning signals."""
    if profile is None:
        return 0.0
    if profile.department_id and candidate.course.department_id == profile.department_id:
        return _DEPARTMENT_BONUS
    if profile.faculty_id and candidate.course.department.faculty_id == profile.faculty_id:
        return _FACULTY_BONUS
    return 0.0


def _apply_context(candidates: list[_Candidate], user) -> None:
    profile = None
    if user is not None:
        profile = (
            StudentProfile.objects.filter(user=user)
            .select_related("department__faculty")
            .first()
        )
    degrees = _prerequisite_degrees()
    offered_ids = set(
        CourseOffering.objects.values_list("course_id", flat=True).distinct()
    )
    for candidate in candidates:
        bonus = _needs_context_bonus(profile, candidate)
        out_n, in_n = degrees.get(candidate.course.pk, (0, 0))
        bonus += min(out_n + in_n, _GRAPH_BONUS_CAP) * _GRAPH_BONUS_PER_EDGE
        if candidate.course.pk in offered_ids:
            bonus += _OFFERED_BONUS
        if normalize_persian(candidate.course.course_type) in _CORE_TYPES:
            bonus += _CORE_TYPE_BONUS
        candidate.context_score = bonus


def _demote_nested_mentions(candidates: list[_Candidate]) -> None:
    """Prefer the fuller course name the user actually typed.

    If candidate A's words are a strict subset of candidate B's words and B's
    full name appears in the question (text_score 1.0), A is almost certainly
    the truncated tail of B's mention, e.g. answered
    «پیش نیاز آزمایشگاه سیستم عامل؟» — A would be «سیستم عامل», B the lab.
    """
    if len(candidates) < 2:
        return
    for index, candidate in enumerate(candidates):
        candidate_tokens = frozenset(candidate.tokens)
        if len(candidate_tokens) < 2:
            continue
        for other_index, other in enumerate(candidates):
            if index == other_index or other.text_score < 1.0:
                continue
            if candidate_tokens < frozenset(other.tokens):
                candidate.text_score -= _NESTED_PENALTY
                break


def resolve_course(question: str, user=None) -> CourseMatch:
    """Resolve a course reference in *question*; never invents a course.

    Ambiguous=True means the context signals could not separate the top two
    candidates (genuine ambiguity — the caller should ask the user which
    course they meant, listing ``matches``). An empty ``matches`` list means
    no reliable candidate exists at all.
    """
    question = (question or "").strip()
    if not question:
        return CourseMatch(None, [], False)

    exact = _match_course_code(question)
    if exact is not None:
        return CourseMatch(exact, [exact], False)

    courses = list(
        Course.objects.filter(active=True).select_related("department__faculty")
    )
    if not courses:
        return CourseMatch(None, [], False)

    question_tokens = _tokens(question)
    candidates = _collect_candidates(
        courses, normalize_persian(question), question_tokens
    )
    if not candidates:
        return CourseMatch(None, [], False)

    _demote_nested_mentions(candidates)
    _apply_context(candidates, user)
    ranked = sorted(
        candidates, key=lambda c: (-c.score, -len(c.title_compact), c.course.code)
    )

    if len(ranked) == 1:
        return CourseMatch(ranked[0].course, [ranked[0].course], False)
    if ranked[0].score - ranked[1].score < _AMBIGUITY_MARGIN:
        return CourseMatch(None, [c.course for c in ranked], True)
    return CourseMatch(ranked[0].course, [c.course for c in ranked], False)
