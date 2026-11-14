"""Phase 11 — deterministic course-selection eligibility engine.

The rules engine *decides*, the LLM only *explains* (AGENTS.md section 8,
docs/18 section "Course selection rule", architecture.md line 18). Every
evaluation is a pure function of PostgreSQL records: the same student, course
and term always produce the same decision, and every rejection carries a
machine-readable reason (``code`` + Persian message + parameters) so the UI
and the explanation layer never have to parse prose —
docs/17-domain-rules.md ("Prerequisite", "Passed course", "Course offering").

Rules implemented, in evaluation order below:

* ``UNKNOWN_COURSE`` — requested code does not exist in the catalog.
* ``ALREADY_PASSED`` — docs/17: a passed course is not recommended again.
  A different catalog code counts as already passed only when the official
  curriculum-transition equivalency holds (see below).
* ``ALREADY_PLANNED`` — the course is already in the current-term planner
  (``PLANNED`` or administratively ``ENROLLED``).
* ``PREREQUISITE_MISSING`` — required ``CoursePrerequisite`` edges whose
  prerequisite course has no ``PASSED`` enrollment. Edges are
  **cohort-aware**: the source data records one rule set per entry-term
  cohort (curriculum revision), so the engine resolves the edges that apply
  to the student's own entry cohort — exact cohort match, else the latest
  revision recorded before their entry, else the oldest one. Edges without
  cohort metadata apply to every cohort (conservative union fallback, as
  before). A missing prerequisite is also satisfied when a passed course is
  its **official curriculum-transition equivalent**: same department, same
  credits, identical normalized title, and the prerequisite rule sets swap
  one code for the other across cohorts (title similarity alone is never
  sufficient).
* ``NOT_OFFERED_CURRENT_TERM`` — docs/17: being in the catalog does not imply
  being offered in the current term.
* ``OFFERING_CLOSED`` — offerings exist in the current term but none is
  ``OPEN``.
* ``CREDIT_LIMIT_EXCEEDED`` — planned + candidate (+ what-if extras) credits
  exceed the configurable per-term limit (OA-24 default).
* ``SCHEDULE_CONFLICT`` — every open *section* of the course overlaps a
  schedule row of the student's current plan (a conflict-free section always
  satisfies the rule: the student cannot be blocked by one full section when
  another fits).

Terminology: "plan" is the student's current-term planner rows
(``Enrollment`` with status in PLANNED/ENROLLED). Passed courses are counted
across *all* terms — history is never rewritten (docs/03 section 5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.academics.models import AcademicTerm
from apps.common.persian import normalize_persian
from apps.courses.models import (
    ClassSchedule,
    Course,
    CourseOffering,
    CoursePrerequisite,
    OfferingStatus,
)
from apps.students.models import Enrollment, EnrollmentStatus, StudentProfile

# ── Machine-readable reason codes (stable API contract) ────────────────────
UNKNOWN_COURSE = "UNKNOWN_COURSE"
ALREADY_PASSED = "ALREADY_PASSED"
ALREADY_PLANNED = "ALREADY_PLANNED"
PREREQUISITE_MISSING = "PREREQUISITE_MISSING"
NOT_OFFERED_CURRENT_TERM = "NOT_OFFERED_CURRENT_TERM"
OFFERING_CLOSED = "OFFERING_CLOSED"
CREDIT_LIMIT_EXCEEDED = "CREDIT_LIMIT_EXCEEDED"
SCHEDULE_CONFLICT = "SCHEDULE_CONFLICT"


def credit_limit() -> int:
    """Per-term credit ceiling (OA-24 baseline: 20, registrar to confirm)."""
    return int(getattr(settings, "COURSE_SELECTION_MAX_TERM_CREDITS", 20))


def student_entry_code(profile: StudentProfile | None) -> str:
    """The student's official entry-term cohort code (fall entry).

    Cohort codes in the source data are ``<last 3 digits of the Jalali entry
    year><semester digit>``, fall entry = ``1``: entry year ``1402`` gives
    ``4021``, ``1394`` gives ``3941``. Empty when the profile has no entry
    year (cohort cannot be resolved).
    """
    year = (getattr(profile, "entry_year", "") or "").strip()
    digits = "".join(ch for ch in year if ch.isdigit())
    if len(digits) != 4:
        return ""
    return f"{digits[1:]}1"


def applicable_prerequisite_edges(
    course: Course, entry_code: str
) -> list[CoursePrerequisite]:
    """Resolve the prerequisite rule set that applies to *entry_code*.

    Each edge carries the official entry-term cohorts it governs
    (``entry_terms``). Resolution order:

    * no cohort metadata anywhere → every edge (union fallback, pre-metadata
      behaviour);
    * the exact cohort has rules → those edges;
    * otherwise the latest revision recorded **before** the student's entry
      (curriculums are cumulative: an older cohort keeps the oldest set).
    """
    edges = list(course.prerequisite_edges.select_related("prerequisite_course"))
    cohort_edges = [edge for edge in edges if edge.entry_terms]
    if not cohort_edges or not entry_code:
        return edges
    cohorts = sorted({term for edge in cohort_edges for term in edge.entry_terms})
    if entry_code in cohorts:
        chosen = entry_code
    else:
        earlier = [cohort for cohort in cohorts if cohort < entry_code]
        chosen = max(earlier) if earlier else cohorts[0]
    return [
        edge for edge in cohort_edges if chosen in edge.entry_terms
    ] + [edge for edge in edges if not edge.entry_terms]


def is_official_equivalent(
    a: Course, b: Course, cache: dict[tuple[str, str], bool] | None = None
) -> bool:
    """Official curriculum-transition equivalency between two catalog codes.

    Two codes are the *same course* under different curriculum versions only
    when the official records agree on all of:

    1. same department;
    2. same credits;
    3. identical normalized title (whitespace/yeh/kaf variants collapse);
    4. swap evidence — some course's prerequisite rule set requires one code
       for earlier cohorts and the other for later ones (disjoint cohort
       lists, i.e. the curriculum replaced one code with the other).

    Title similarity alone is never sufficient (docs/17 "Insufficient
    evidence"). Results are memoized per evaluation in *cache*.
    """
    if a.pk == b.pk:
        return True
    key = (min(a.code, b.code), max(a.code, b.code))
    if cache is not None and key in cache:
        return cache[key]
    result = (
        a.department_id == b.department_id
        and a.credits == b.credits
        and normalize_persian(a.title) == normalize_persian(b.title)
        and _swap_evidence(a, b)
    )
    if cache is not None:
        cache[key] = result
    return result


def _swap_evidence(a: Course, b: Course) -> bool:
    """Did a curriculum revision replace `a` with `b` in a rule set?"""
    edges = CoursePrerequisite.objects.filter(
        prerequisite_course_id__in=[a.pk, b.pk]
    ).select_related("prerequisite_course")
    # course -> prerequisite course -> cohort codes requiring it
    by_course: dict[int, dict[int, set[str]]] = {}
    for edge in edges:
        if not edge.entry_terms:
            continue
        slots = by_course.setdefault(edge.course_id, {})
        slots.setdefault(edge.prerequisite_course_id, set()).update(edge.entry_terms)
    for slots in by_course.values():
        a_terms = slots.get(a.pk)
        b_terms = slots.get(b.pk)
        # Disjoint cohort lists for the same rule slot = one code replaced
        # the other across a curriculum transition.
        if a_terms and b_terms and not (a_terms & b_terms):
            return True
    return False


@dataclass(frozen=True)
class SelectionReason:
    """One machine-readable rejection (or rule) outcome."""

    code: str
    message: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "params": self.params}


@dataclass
class SelectionDecision:
    """Full, serialisable engine outcome for one (student, course) pair."""

    course_code: str
    course_title: str
    course_credits: int
    eligible: bool
    reasons: list[SelectionReason]
    term_name: str
    passed_course_codes: list[str]
    missing_prerequisite_codes: list[str]
    planned_course_codes: list[str]
    planned_credits: int
    extra_course_codes: list[str]
    extra_credits: int
    credit_limit: int

    def to_dict(self) -> dict[str, Any]:
        total = self.planned_credits + self.course_credits + self.extra_credits
        return {
            "course": {
                "code": self.course_code,
                "title": self.course_title,
                "credits": self.course_credits,
            },
            "eligible": self.eligible,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "term_name": self.term_name,
            "passed_course_codes": self.passed_course_codes,
            "missing_prerequisite_codes": self.missing_prerequisite_codes,
            "planned_course_codes": self.planned_course_codes,
            "extra_course_codes": self.extra_course_codes,
            "credit_totals": {
                "limit": self.credit_limit,
                # Without the hypothetical extras — the committed plan.
                "planned": self.planned_credits,
                "candidate": self.course_credits,
                "extra": self.extra_credits,
                # With the candidate + extras — the what-if total.
                "total_with_candidate": total,
                "over_limit": total > self.credit_limit,
            },
            "engine_version": "phase11-rules-v1",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelectionDecision:
        """Rebuild from :meth:`to_dict` (used by the explanation layer)."""
        reasons = [
            SelectionReason(
                code=reason["code"],
                message=reason["message"],
                params=reason.get("params") or {},
            )
            for reason in data["reasons"]
        ]
        course = data["course"]
        totals = data["credit_totals"]
        return cls(
            course_code=course["code"],
            course_title=course["title"],
            course_credits=course["credits"],
            eligible=data["eligible"],
            reasons=reasons,
            term_name=data["term_name"],
            passed_course_codes=data["passed_course_codes"],
            missing_prerequisite_codes=data["missing_prerequisite_codes"],
            planned_course_codes=data["planned_course_codes"],
            planned_credits=totals["planned"],
            extra_course_codes=data["extra_course_codes"],
            extra_credits=totals["extra"],
            credit_limit=totals["limit"],
        )


class CourseSelectionEngine:
    """Deterministic eligibility evaluation against PostgreSQL records."""

    def __init__(self, limit: int | None = None) -> None:
        self._limit_override = limit

    def evaluate(
        self,
        user,
        course_code: str,
        extra_course_codes: list[str] | None = None,
    ) -> SelectionDecision:
        limit = self._limit_override if self._limit_override is not None else credit_limit()
        wanted = normalize_persian(course_code or "")
        # What-if extras: deduped, never the candidate itself.
        extras: list[str] = []
        for raw_code in extra_course_codes or []:
            code = normalize_persian(str(raw_code or ""))
            if code and code != wanted and code not in extras:
                extras.append(code)

        course = Course.objects.filter(code__iexact=wanted).first()
        if course is None:
            return SelectionDecision(
                course_code=wanted,
                course_title="",
                course_credits=0,
                eligible=False,
                reasons=[
                    SelectionReason(
                        code=UNKNOWN_COURSE,
                        message="درسی با این کد در پایگاه داده وجود ندارد.",
                        params={"course_code": wanted},
                    )
                ],
                term_name="",
                passed_course_codes=[],
                missing_prerequisite_codes=[],
                planned_course_codes=[],
                planned_credits=0,
                extra_course_codes=extras,
                extra_credits=0,
                credit_limit=limit,
            )

        term = AcademicTerm.objects.filter(is_current=True).first()
        term_name = getattr(term, "name", "") if term is not None else ""
        reasons: list[SelectionReason] = []

        profile = StudentProfile.objects.filter(user=user).first()
        passed_codes: list[str] = []
        passed_courses: dict[str, Course] = {}
        if profile is not None:
            passed_qs = Enrollment.objects.filter(
                student=profile, status=EnrollmentStatus.PASSED
            ).select_related("course_offering__course", "course_offering__term")
            for enrollment in passed_qs:
                passed_course = enrollment.course_offering.course
                passed_codes.append(passed_course.code)
                passed_courses[passed_course.code] = passed_course
            passed_codes = sorted(passed_codes)

        plan_credits = 0
        planned_codes: list[str] = []
        plan_schedules: list[tuple[str, ClassSchedule]] = []  # (course_title, row)
        if profile is not None and term is not None:
            plan_rows = (
                Enrollment.objects.filter(
                    student=profile,
                    status__in=[EnrollmentStatus.PLANNED, EnrollmentStatus.ENROLLED],
                    course_offering__term=term,
                )
                .select_related("course_offering__course")
                .prefetch_related("course_offering__schedules")
            )
            for row in plan_rows:
                plan_course = row.course_offering.course
                planned_codes.append(plan_course.code)
                plan_credits += plan_course.credits
                for schedule in row.course_offering.schedules.all():
                    plan_schedules.append((plan_course.title, schedule))
        planned_codes = sorted(set(planned_codes))

        # Equivalency results are memoized per evaluation (the same pair is
        # checked by both the ALREADY_PASSED and the prerequisite rules).
        equivalency_cache: dict[tuple[str, str], bool] = {}
        # docs/17 "Passed course": no silent repetition. A different catalog
        # code counts as already passed only with an official equivalency.
        already_passed = course.code in passed_codes or any(
            is_official_equivalent(course, passed, equivalency_cache)
            for passed in passed_courses.values()
        )
        if already_passed:
            reasons.append(
                SelectionReason(
                    code=ALREADY_PASSED,
                    message="این درس را قبلاً با موفقیت گذرانده‌اید؛ تکرار آن پیشنهاد نمی‌شود.",
                    params={"course_code": course.code},
                )
            )
        if course.code in planned_codes:
            reasons.append(
                SelectionReason(
                    code=ALREADY_PLANNED,
                    message="این درس هم‌اکنون در برنامه ترم جاری شماست.",
                    params={"course_code": course.code},
                )
            )

        # Prerequisites must all be passed (docs/17 "Prerequisite"), resolved
        # for the student's own entry cohort and satisfied by an official
        # curriculum-transition equivalent of a passed course.
        entry_code = student_entry_code(profile)
        applicable_edges = applicable_prerequisite_edges(course, entry_code)
        required_courses = {
            edge.prerequisite_course.code: edge.prerequisite_course
            for edge in applicable_edges
        }
        missing = [
            code
            for code in sorted(required_courses)
            if code not in passed_codes
            and not any(
                is_official_equivalent(required_courses[code], passed, equivalency_cache)
                for passed in passed_courses.values()
            )
        ]
        if missing:
            reasons.append(
                SelectionReason(
                    code=PREREQUISITE_MISSING,
                    message=(
                        "ابتدا باید این پیش‌نیازها را با موفقیت بگذرانید: "
                        f"{', '.join(missing)}"
                    ),
                    params={"codes": missing, "count": len(missing)},
                )
            )

        # Availability in the *current* term only (docs/17 "Course offering").
        if term is None:
            reasons.append(
                SelectionReason(
                    code=NOT_OFFERED_CURRENT_TERM,
                    message="ترم جاری تعریف نشده است.",
                    params={"course_code": course.code},
                )
            )
        else:
            offerings = list(
                CourseOffering.objects.filter(term=term, course=course)
                .select_related("course", "term")
                .prefetch_related("schedules")
                .order_by("section_code")
            )
            if not offerings:
                reasons.append(
                    SelectionReason(
                        code=NOT_OFFERED_CURRENT_TERM,
                        message="این درس در ترم جاری ارائه نشده است.",
                        params={"course_code": course.code, "term": term_name},
                    )
                )
            else:
                open_offerings = [
                    offering
                    for offering in offerings
                    if offering.status == OfferingStatus.OPEN
                ]
                if not open_offerings:
                    reasons.append(
                        SelectionReason(
                            code=OFFERING_CLOSED,
                            message="ارائه ترم جاری این درس بسته یا لغوشده است.",
                            params={
                                "course_code": course.code,
                                "term": term_name,
                                "sections": [offering.section_code for offering in offerings],
                            },
                        )
                    )
                else:
                    if (
                        self._pick_conflict_free_section(open_offerings, plan_schedules)
                        is None
                    ):
                        reasons.append(
                            SelectionReason(
                                code=SCHEDULE_CONFLICT,
                                message=(
                                    "همه گروه‌های باز این درس با زمان‌بندی درس‌های "
                                    "برنامه فعلی شما تداخل دارند."
                                ),
                                params={
                                    "course_code": course.code,
                                    "term": term_name,
                                    "sections": [
                                        offering.section_code for offering in open_offerings
                                    ],
                                },
                            )
                        )

        # Credit limit over the committed plan + candidate + what-if extras.
        extra_credits = 0
        resolved_extras: list[str] = []
        for code in extras:
            extra_course = Course.objects.filter(code__iexact=code).first()
            if extra_course is None:
                continue
            extra_credits += extra_course.credits
            resolved_extras.append(extra_course.code)
        total_with_candidate = plan_credits + course.credits + extra_credits
        if total_with_candidate > limit:
            reasons.append(
                SelectionReason(
                    code=CREDIT_LIMIT_EXCEEDED,
                    message=(
                        f"جمع واحدهای ترم ({total_with_candidate}) از سقف مجاز "
                        f"({limit}) بیشتر است."
                    ),
                    params={
                        "limit": limit,
                        "planned": plan_credits,
                        "candidate": course.credits,
                        "extra": extra_credits,
                        "total": total_with_candidate,
                    },
                )
            )

        return SelectionDecision(
            course_code=course.code,
            course_title=course.title,
            course_credits=course.credits,
            eligible=not reasons,
            reasons=reasons,
            term_name=term_name,
            passed_course_codes=passed_codes,
            missing_prerequisite_codes=missing,
            planned_course_codes=planned_codes,
            planned_credits=plan_credits,
            extra_course_codes=resolved_extras,
            extra_credits=extra_credits,
            credit_limit=limit,
        )

    @staticmethod
    def _pick_conflict_free_section(
        open_offerings: list[CourseOffering],
        plan_schedules: list[tuple[str, ClassSchedule]],
    ) -> CourseOffering | None:
        """First open section (by section code) that fits the current plan.

        The student cannot be blocked when *some* section exists without
        overlap — deterministic because sections are ordered and schedules
        collected in a fixed order.
        """
        for offering in open_offerings:
            candidate_rows = list(offering.schedules.all())
            conflicts: list[dict[str, Any]] = []
            for planner_title, planner_row in plan_schedules:
                for candidate_row in candidate_rows:
                    if _overlaps(candidate_row, planner_row):
                        conflicts.append(
                            {
                                "weekday": candidate_row.weekday,
                                "start": candidate_row.start_time.strftime("%H:%M"),
                                "end": candidate_row.end_time.strftime("%H:%M"),
                                "planned_course": planner_title,
                            }
                        )
            if not conflicts:
                return offering
        return None


def _overlaps(a: ClassSchedule, b: ClassSchedule) -> bool:
    """Same weekday with intersecting time ranges."""
    return (
        a.weekday == b.weekday
        and a.start_time < b.end_time
        and b.start_time < a.end_time
    )
