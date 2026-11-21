"""Course-resolution tests — code *or* Persian name, deterministic and safe.

The lookup layer only maps the student's query to a catalog row; the engine is
untouched. These tests pin the priority order (exact code → exact normalized
title → unique containment → ambiguity/not-found), the Persian normalization
variants, and the endpoint contract that feeds the *resolved* real code into
``CourseSelectionEngine``.
"""

from __future__ import annotations

import pytest

from apps.courses.models import Course
from apps.students.course_lookup import MAX_CANDIDATES, resolve_course

pytestmark = pytest.mark.django_db


@pytest.fixture
def titled_courses(academic_graph):
    """Two catalog rows whose normalized titles collide, plus unique ones."""
    department = academic_graph["department"]
    first = Course.objects.create(
        department=department,
        code="1916010",
        title="نظریه زبان‌ها و ماشین‌ها",
        credits=3,
    )
    second = Course.objects.create(
        department=department,
        code="1916011",
        title="نظریه زبانها و ماشینها",
        credits=3,
    )
    networks = Course.objects.create(
        department=department,
        code="1916020",
        title="شبکه‌های کامپیوتری",
        credits=3,
    )
    lab = Course.objects.create(
        department=department,
        code="1916021",
        title="آزمایشگاه شبکه‌های کامپیوتری",
        credits=1,
    )
    return {
        **academic_graph,
        "theory_a": first,
        "theory_b": second,
        "networks": networks,
        "lab": lab,
    }


# ── priority 1: exact code ──────────────────────────────────────────────────


def test_exact_code_resolves(titled_courses):
    match = resolve_course("1916010")
    assert match.status == "resolved"
    assert match.course.code == "1916010"


def test_persian_digit_code_resolves(academic_graph):
    match = resolve_course("۱۹۱۶۰۰۱")
    assert match.status == "resolved"
    assert match.course.code == academic_graph["course"].code


# ── priority 2: exact normalized title ──────────────────────────────────────


def test_exact_title_with_spaces_matches_half_space_catalog_title(titled_courses):
    match = resolve_course("نظریه زبان ها و ماشین ها")
    assert match.status == "ambiguous"  # both rows collide after normalization
    assert {candidate.code for candidate in match.candidates} == {"1916010", "1916011"}


def test_exact_title_with_half_space_resolves_unique_title(titled_courses):
    match = resolve_course("آزمایشگاه شبکه‌های کامپیوتری")
    assert match.status == "resolved"
    assert match.course.code == "1916021"


def test_space_variants_match_a_unique_half_space_title(academic_graph):
    """The documented example: catalog ZWNJ title, student types plain spaces."""
    Course.objects.create(
        department=academic_graph["department"],
        code="1916030",
        title="ساختمان داده‌ها",
        credits=3,
    )
    match = resolve_course("  ساختمان   داده ها  ")
    assert match.status == "resolved"
    assert match.course.code == "1916030"


def test_exact_title_beats_containment_priority(academic_graph):
    """Priority 2 must win over priority 3, not merge into ambiguity."""
    department = academic_graph["department"]
    exact = Course.objects.create(
        department=department, code="1916031", title="شبکه", credits=3
    )
    Course.objects.create(
        department=department, code="1916032", title="شبکه‌های کامپیوتری", credits=3
    )
    match = resolve_course("شبکه")
    assert match.status == "resolved"
    assert match.course.code == exact.code


def test_arabic_yeh_and_kaf_variants_resolve(academic_graph):
    match = resolve_course("مبانى برنامه‌سازى")
    assert match.status == "resolved"
    assert match.course.code == academic_graph["prereq"].code


def test_punctuation_differences_resolve(titled_courses):
    match = resolve_course("شبکه های کامپیوتری!")
    assert match.status == "resolved"
    assert match.course.code == "1916020"


# ── priority 3: unique containment ──────────────────────────────────────────


def test_unique_containment_resolves(titled_courses):
    match = resolve_course("آزمایشگاه شبکه‌های")
    assert match.status == "resolved"
    assert match.course.code == "1916021"


def test_broad_containment_is_ambiguous_never_auto_selected(titled_courses):
    match = resolve_course("شبکه")
    assert match.status == "ambiguous"
    assert match.course is None
    assert match.total == 2


def test_containment_shorter_than_the_guard_is_not_found(titled_courses):
    match = resolve_course("شبک")
    # Below MIN_CONTAINMENT_LENGTH: no accidental substring match at all.
    assert match.status == "not_found"
    assert match.course is None


# ── ambiguity and not-found ─────────────────────────────────────────────────


def test_identical_normalized_titles_are_ambiguous(titled_courses):
    match = resolve_course("نظریه زبان‌ها و ماشین‌ها")
    assert match.status == "ambiguous"
    assert match.course is None
    assert match.total == 2


def test_similar_titles_are_not_confused(titled_courses):
    match = resolve_course("شبکه‌های کامپیوتر")
    assert match.status == "ambiguous"
    assert match.course is None
    codes = {candidate.code for candidate in match.candidates}
    assert codes == {"1916020", "1916021"}


def test_unknown_query_is_not_found(titled_courses):
    match = resolve_course("درس کاملاً ناموجود")
    assert match.status == "not_found"
    assert match.course is None
    assert match.candidates == []


def test_empty_query_is_not_found():
    assert resolve_course("   ").status == "not_found"


# ── REST surface ────────────────────────────────────────────────────────────


def test_endpoint_accepts_a_persian_title_and_passes_the_resolved_code(
    titled_courses, authed_client, student, student_profile
):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_query": "آزمایشگاه شبکه‌های کامپیوتری"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    # The engine received the catalog code, not the typed Persian name.
    assert body["course"]["code"] == "1916021"
    assert body["course"]["title"] == "آزمایشگاه شبکه‌های کامپیوتری"
    # Existing rules still run: no current-term offering for this course.
    assert body["eligible"] is False
    assert "NOT_OFFERED_CURRENT_TERM" in [reason["code"] for reason in body["reasons"]]


def test_endpoint_still_accepts_the_legacy_course_code_field(
    academic_graph, authed_client, student, student_profile
):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": academic_graph["course"].code},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["course"]["code"] == academic_graph["course"].code


def test_name_and_code_produce_the_identical_engine_decision(
    academic_graph, authed_client, student, student_profile
):
    """The lookup layer only resolves the course; every rule stays untouched.

    Asking by the catalog's Persian title must return exactly the same verdict,
    reasons and credit totals as asking by its numeric code.
    """
    client = authed_client(student)
    course = academic_graph["prereq"]
    by_code = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": course.code},
        format="json",
    )
    by_name = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_query": course.title},
        format="json",
    )
    assert by_code.status_code == by_name.status_code == 200
    assert by_name.json() == by_code.json()
    # And the existing offering rule really did run for the resolved row.
    assert "NOT_OFFERED_CURRENT_TERM" in [
        reason["code"] for reason in by_name.json()["reasons"]
    ]


def test_endpoint_returns_candidates_for_an_ambiguous_title(
    titled_courses, authed_client, student, student_profile
):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_query": "نظریه زبان ها و ماشین ها"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ambiguous"
    # No verdict is produced for an ambiguous title.
    assert "eligible" not in body
    assert "reasons" not in body
    assert body["total"] == 2
    assert [candidate["code"] for candidate in body["candidates"]] == ["1916010", "1916011"]
    candidate = body["candidates"][0]
    assert candidate["title"]
    assert candidate["credits"] == 3
    assert candidate["department"] == titled_courses["department"].name


def test_ambiguous_candidates_are_capped(academic_graph):
    department = academic_graph["department"]
    for index in range(MAX_CANDIDATES + 5):
        Course.objects.create(
            department=department,
            code=f"19200{index:02d}",
            title=f"درس همسان شماره {index:02d}",
            credits=2,
        )
    match = resolve_course("درس همسان")
    assert match.status == "ambiguous"
    assert match.total == MAX_CANDIDATES + 5
    assert len(match.candidates) == MAX_CANDIDATES


def test_endpoint_404s_with_a_clear_persian_message(
    titled_courses, authed_client, student, student_profile
):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_query": "نام کاملاً ناموجود"},
        format="json",
    )
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert "کد درس یا نام دقیق" in error["message"]
    assert error["details"]["query"] == "نام کاملاً ناموجود"


def test_endpoint_requires_a_query(authed_client, student):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/", {"course_query": "  "}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
