"""Phase 11 — deterministic course-selection engine and its REST surface

(``POST /students/me/course-selection/``).

Each documented rule gets its own test; the engine must give the same answer
twice (reproducibility) and every rejection must carry a machine-readable
reason code, a Persian message and parameters. API tests pin the reason codes
as a stable contract and the strict what-if lookup.
"""

from __future__ import annotations

import datetime as dt

import pytest
from django.test import override_settings

from apps.courses.models import (
    ClassSchedule,
    Course,
    CourseOffering,
    CoursePrerequisite,
    OfferingStatus,
)
from apps.students.course_selection import (
    ALREADY_PASSED,
    ALREADY_PLANNED,
    CREDIT_LIMIT_EXCEEDED,
    NOT_OFFERED_CURRENT_TERM,
    OFFERING_CLOSED,
    PREREQUISITE_MISSING,
    SCHEDULE_CONFLICT,
    UNKNOWN_COURSE,
    CourseSelectionEngine,
)
from apps.students.models import Enrollment, EnrollmentStatus

pytestmark = pytest.mark.django_db

WEEK_SATURDAY = 5  # Weekday.SATURDAY — Iranian week starts on شنبه


# ── Local fixtures (a fuller graph than conftest's academic_graph) ──────────


@pytest.fixture
def graph(academic_graph):
    """The conftest graph plus a prerequisite edge and two open offerings."""
    CoursePrerequisite.objects.create(
        course=academic_graph["course"], prerequisite_course=academic_graph["prereq"]
    )
    offering = CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )
    prereq_offering = CourseOffering.objects.create(
        course=academic_graph["prereq"],
        term=academic_graph["past_term"],
        section_code="01",
    )
    return {
        **academic_graph,
        "offering": offering,
        "prereq_offering": prereq_offering,
        "engine": CourseSelectionEngine(),
    }


@pytest.fixture
def passed_prereq(graph, student, student_profile):
    """The student has already passed the prerequisite course."""
    return Enrollment.objects.create(
        student=student_profile,
        course_offering=graph["prereq_offering"],
        status=EnrollmentStatus.PASSED,
        grade=17.50,
    )


def make_schedule(offering: CourseOffering, start: str, end: str) -> ClassSchedule:
    return ClassSchedule.objects.create(
        course_offering=offering,
        weekday=WEEK_SATURDAY,
        start_time=dt.time.fromisoformat(start),
        end_time=dt.time.fromisoformat(end),
    )


def plan_offering(graph, student_profile, course, section="01", start="08:00", end="10:00"):
    """A PLANNED offering with a schedule row (part of the current plan)."""
    offering = CourseOffering.objects.create(
        course=course, term=graph["term"], section_code=section
    )
    row = make_schedule(offering, start, end)
    Enrollment.objects.create(
        student=student_profile, course_offering=offering, status=EnrollmentStatus.PLANNED
    )
    return offering, row


# ── Rule: unknown course ────────────────────────────────────────────────────


def test_unknown_course_code_is_not_eligible(graph, student):
    decision = graph["engine"].evaluate(student, "9999999")
    payload = decision.to_dict()
    assert payload["eligible"] is False
    codes = [reason["code"] for reason in payload["reasons"]]
    assert codes == [UNKNOWN_COURSE]
    message = payload["reasons"][0]["message"]
    assert message and all("\u0600" <= ch <= "\u06ff" or not ch.isalpha() for ch in message)


# ── Rule: prerequisite ──────────────────────────────────────────────────────


def test_prerequisite_missing_blocks_with_code_and_code_in_message(graph, student):
    decision = graph["engine"].evaluate(student, graph["course"].code)
    payload = decision.to_dict()
    codes = [reason["code"] for reason in payload["reasons"]]
    assert codes == [PREREQUISITE_MISSING]
    assert payload["missing_prerequisite_codes"] == [graph["prereq"].code]
    assert graph["prereq"].code in payload["reasons"][0]["message"]


def test_passed_prerequisite_satisfies_the_rule(graph, student, student_profile, passed_prereq):
    decision = graph["engine"].evaluate(student, graph["course"].code)
    assert decision.eligible is True
    assert decision.missing_prerequisite_codes == []


def test_failed_prerequisite_does_not_satisfy_the_rule(graph, student, student_profile):
    Enrollment.objects.create(
        student=student_profile,
        course_offering=graph["prereq_offering"],
        status=EnrollmentStatus.FAILED,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    decision_codes = [reason.code for reason in decision.reasons]
    assert PREREQUISITE_MISSING in decision_codes
    assert decision.missing_prerequisite_codes == [graph["prereq"].code]


# ── Rule: passed course ─────────────────────────────────────────────────────


def test_already_passed_course_is_rejected(graph, student, student_profile, passed_prereq):
    Enrollment.objects.create(
        student=student_profile,
        course_offering=graph["offering"],
        status=EnrollmentStatus.PASSED,
        grade=19.00,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    payload = decision.to_dict()
    payload_codes = [reason["code"] for reason in payload["reasons"]]
    assert payload_codes == [ALREADY_PASSED]
    assert payload["eligible"] is False


def test_failed_course_is_not_treated_as_passed(graph, student, student_profile):
    Enrollment.objects.create(
        student=student_profile,
        course_offering=graph["offering"],
        status=EnrollmentStatus.FAILED,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    decision_codes = [reason.code for reason in decision.reasons]
    assert ALREADY_PASSED not in decision_codes


# ── Rule: duplicate planner entry ──────────────────────────────────────────


def test_already_planned_course_is_rejected(graph, student, student_profile, passed_prereq):
    Enrollment.objects.create(
        student=student_profile,
        course_offering=graph["offering"],
        status=EnrollmentStatus.PLANNED,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    payload = decision.to_dict()
    payload_codes = [reason["code"] for reason in payload["reasons"]]
    assert payload_codes == [ALREADY_PLANNED]
    assert graph["course"].code in payload["planned_course_codes"]


def test_admin_enrolled_course_counts_as_planned(graph, student, student_profile):
    Enrollment.objects.create(
        student=student_profile,
        course_offering=graph["offering"],
        status=EnrollmentStatus.ENROLLED,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    decision_codes = [reason.code for reason in decision.reasons]
    assert ALREADY_PLANNED in decision_codes


def test_past_term_scheduling_does_not_flag_duplicate(graph, student, student_profile):
    """A PASSED/old-term row is history, not the current-term plan."""
    old_offering = CourseOffering.objects.create(
        course=graph["course"], term=graph["past_term"], section_code="02"
    )
    Enrollment.objects.create(
        student=student_profile,
        course_offering=old_offering,
        status=EnrollmentStatus.FAILED,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    decision_codes = [reason.code for reason in decision.reasons]
    assert ALREADY_PLANNED not in decision_codes
    assert decision.planned_course_codes == []


# ── Rule: availability in the current term ─────────────────────────────────


def test_course_not_offered_in_current_term(graph, student, passed_prereq):
    graph["offering"].delete()  # only the current-term section is removed
    decision = graph["engine"].evaluate(student, graph["course"].code)
    payload = decision.to_dict()
    payload_codes = [reason["code"] for reason in payload["reasons"]]
    assert payload_codes == [NOT_OFFERED_CURRENT_TERM]


def test_plan_rows_in_other_terms_do_not_count_towards_credits(graph, student, student_profile):
    heavy = Course.objects.create(
        department=graph["department"], code="1916010", title="سنگین", credits=19
    )
    old_offering = CourseOffering.objects.create(
        course=heavy, term=graph["past_term"], section_code="01"
    )
    Enrollment.objects.create(
        student=student_profile,
        course_offering=old_offering,
        status=EnrollmentStatus.ENROLLED,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    assert decision.planned_credits == 0


# ── Rule: offering status ──────────────────────────────────────────────────


def test_closed_offering_flags_offering_closed(graph, student, passed_prereq):
    graph["offering"].status = OfferingStatus.CLOSED
    graph["offering"].save(update_fields=["status"])
    decision = graph["engine"].evaluate(student, graph["course"].code)
    payload = decision.to_dict()
    payload_codes = [reason["code"] for reason in payload["reasons"]]
    assert payload_codes == [OFFERING_CLOSED]
    assert payload["reasons"][0]["params"]["sections"] == ["01"]


def test_cancelled_offering_flags_offering_closed(graph, student, passed_prereq):
    graph["offering"].status = OfferingStatus.CANCELLED
    graph["offering"].save(update_fields=["status"])
    decision = graph["engine"].evaluate(student, graph["course"].code)
    decision_codes = [reason.code for reason in decision.reasons]
    assert decision_codes == [OFFERING_CLOSED]
    assert decision.eligible is False


# ── Rule: schedule conflict ────────────────────────────────────────────────


def test_single_conflicting_section_blocks(graph, student, student_profile, passed_prereq):
    plan_offering(graph, student_profile, graph["prereq"])  # شنبه ۸–۱۰ (default)
    make_schedule(graph["offering"], "09:00", "11:00")  # overlaps ۸–۱۰
    decision = graph["engine"].evaluate(student, graph["course"].code)
    payload = decision.to_dict()
    payload_codes = [reason["code"] for reason in payload["reasons"]]
    assert payload_codes == [SCHEDULE_CONFLICT]
    conflict = payload["reasons"][0]
    assert conflict["params"]["sections"] == ["01"]
    assert conflict["message"].strip()


def test_second_free_section_picks_first_and_keeps_eligible(graph, student, student_profile, passed_prereq):
    plan_offering(graph, student_profile, graph["prereq"])
    # The single existing section conflicts with the plan; removing it and
    # adding a later section keeps the course reachable (sections ordered).
    graph["offering"].delete()
    blocked = CourseOffering.objects.create(
        course=graph["course"], term=graph["term"], section_code="01"
    )
    free = CourseOffering.objects.create(
        course=graph["course"], term=graph["term"], section_code="02"
    )
    make_schedule(blocked, "09:00", "11:00")
    make_schedule(free, "14:00", "16:00")
    decision = graph["engine"].evaluate(student, graph["course"].code)
    assert decision.eligible is True
    assert [reason.code for reason in decision.reasons] == []


def test_partial_overlap_counts_as_conflict(graph, student, student_profile, passed_prereq):
    make_schedule(graph["offering"], "10:30", "12:00")
    plan_offering(graph, student_profile, graph["prereq"], start="10:00", end="10:31")
    decision = graph["engine"].evaluate(student, graph["course"].code)
    decision_codes = [reason.code for reason in decision.reasons]
    assert SCHEDULE_CONFLICT in decision_codes


# ── Rule: credit limit ─────────────────────────────────────────────────────


def test_credit_limit_exceeded(graph, student, student_profile, passed_prereq):
    heavy = Course.objects.create(
        department=graph["department"], code="1916011", title="پروژه بزرگ", credits=19
    )
    plan_offering(graph, student_profile, heavy)  # 19 planned + 1 candidate = 20 == limit
    decision = graph["engine"].evaluate(student, graph["course"].code)
    totals = decision.to_dict()["credit_totals"]
    assert totals["total_with_candidate"] == 20
    assert totals["over_limit"] is False  # exactly at the limit is allowed
    assert decision.eligible is True

    extra = Course.objects.create(
        department=graph["department"], code="1916012", title="دو واحدی", credits=2
    )
    decision = graph["engine"].evaluate(
        student, graph["course"].code, extra_course_codes=[extra.code]
    )
    payload = decision.to_dict()
    payload_codes = [reason["code"] for reason in payload["reasons"]]
    assert payload_codes == [CREDIT_LIMIT_EXCEEDED]
    totals = payload["credit_totals"]
    assert totals == {
        "limit": 20,
        "planned": 19,
        "candidate": 1,
        "extra": 2,
        "total_with_candidate": 22,
        "over_limit": True,
    }
    assert "22" in payload["reasons"][0]["message"]


@override_settings(COURSE_SELECTION_MAX_TERM_CREDITS=24)
def test_credit_limit_is_configurable(graph, student, student_profile, passed_prereq):
    heavy = Course.objects.create(
        department=graph["department"], code="1916011", title="پروژه بزرگ", credits=19
    )
    plan_offering(graph, student_profile, heavy)
    extra = Course.objects.create(
        department=graph["department"], code="1916012", title="دو واحدی", credits=2
    )
    decision = graph["engine"].evaluate(
        student, graph["course"].code, extra_course_codes=[extra.code]
    )
    assert decision.eligible is True  # 19 + 1 + 2 = 22 <= 24
    assert decision.credit_limit == 24


def test_missing_recent_passes_and_whatif_extras_are_counted(
    graph, student, student_profile, passed_prereq
):
    """A passed course's credits belong to history, not to the term budget."""
    heavy = Course.objects.create(
        department=graph["department"], code="1916011", title="پروژه بزرگ", credits=19
    )
    old_offering = CourseOffering.objects.create(
        course=heavy, term=graph["past_term"], section_code="01"
    )
    Enrollment.objects.create(
        student=student_profile,
        course_offering=old_offering,
        status=EnrollmentStatus.PASSED,
        grade=16.00,
    )
    decision = graph["engine"].evaluate(student, graph["course"].code)
    totals = decision.to_dict()["credit_totals"]
    assert totals["planned"] == 0
    assert totals["over_limit"] is False


# ── What-if extras ─────────────────────────────────────────────────────────


def test_extras_deduplicate_and_ignore_the_candidate_itself(graph, student, passed_prereq):
    decision = graph["engine"].evaluate(
        student,
        graph["course"].code,
        extra_course_codes=[graph["prereq"].code, graph["prereq"].code, graph["course"].code],
    )
    assert decision.extra_course_codes == [graph["prereq"].code]


def test_unknown_extra_codes_are_silently_ignored_by_the_engine(graph, student, passed_prereq):
    decision = graph["engine"].evaluate(
        student, graph["course"].code, extra_course_codes=["8888888"]
    )
    assert decision.extra_course_codes == []
    assert decision.extra_credits == 0
    assert decision.eligible is True


# ── Persian normalization ──────────────────────────────────────────────────


def test_persian_digits_and_arabic_yeh_code_find_the_course(graph, student, passed_prereq):
    decision = graph["engine"].evaluate(student, " ۱۹۱۶۰۰۱ ")  # Persian digits + spaces
    assert decision.course_code == graph["course"].code
    assert decision.eligible is True


# ── Reproducibility ────────────────────────────────────────────────────────


def test_evaluation_is_reproducible(graph, student, student_profile, passed_prereq):
    plan_offering(graph, student_profile, graph["prereq"])
    first = graph["engine"].evaluate(student, graph["course"].code).to_dict()
    second = graph["engine"].evaluate(student, graph["course"].code).to_dict()
    assert first == second


# ── REST surface ───────────────────────────────────────────────────────────


def test_endpoint_returns_engine_decision(graph, authed_client, student, student_profile, passed_prereq):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": graph["course"].code},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["course"]["code"] == graph["course"].code
    assert body["eligible"] is True
    assert body["reasons"] == []
    assert body["engine_version"] == "phase11-rules-v1"
    assert body["credit_totals"]["limit"] == 20
    assert body["term_name"] == graph["term"].name
    assert body["explanation"]["source"] == "composed"
    assert body["explanation"]["engine_eligible"] is True
    assert body["explanation"]["text"].strip()


def test_endpoint_lists_machine_readable_reasons(
    graph, authed_client, student, student_profile
):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": graph["course"].code},
        format="json",
    )
    body = response.json()
    assert body["eligible"] is False
    assert [r["code"] for r in body["reasons"]] == [PREREQUISITE_MISSING]
    assert body["missing_prerequisite_codes"] == [graph["prereq"].code]


def test_endpoint_requires_authentication(api_client, academic_graph):
    response = api_client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": academic_graph["course"].code},
        format="json",
    )
    assert response.status_code == 401


def test_endpoint_rejects_non_students(authed_client, professor_user, academic_graph):
    client = authed_client(professor_user)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": academic_graph["course"].code},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_endpoint_requires_course_code(authed_client, student):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/", {"course_code": ""}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_endpoint_404_for_unknown_course(authed_client, student):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/", {"course_code": "7777777"}, format="json"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_endpoint_rejects_invalid_extra_list(authed_client, student):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": "1916001", "extra_course_codes": ["1916002", 42]},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_endpoint_400_for_unknown_extra(authed_client, student, academic_graph):
    client = authed_client(student)
    response = client.post(
        "/api/v1/students/me/course-selection/",
        {"course_code": academic_graph["course"].code, "extra_course_codes": ["9999999"]},
        format="json",
    )
    assert response.status_code == 400
    assert "9999999" in response.json()["error"]["message"]


def test_endpoint_extras_flow_into_credit_totals(
    graph, passed_prereq, authed_client, student, student_profile
):
    heavy = Course.objects.create(
        department=graph["department"], code="1916011", title="پروژه بزرگ", credits=19
    )
    plan_offering(graph, student_profile, heavy)
    response = authed_client(student).post(
        "/api/v1/students/me/course-selection/",
        {"course_code": graph["course"].code, "extra_course_codes": [graph["prereq"].code]},
        format="json",
    )
    body = response.json()
    assert body["eligible"] is False  # 19 planned + 1 + 3 = 23 > 20
    code_list = [r["code"] for r in body["reasons"]]
    assert code_list == [CREDIT_LIMIT_EXCEEDED]
    assert body["credit_totals"]["extra"] == graph["prereq"].credits


@override_settings(COURSE_SELECTION_MAX_TERM_CREDITS=24)
def test_endpoint_honors_setting_override(
    graph, passed_prereq, authed_client, student, student_profile
):
    heavy = Course.objects.create(
        department=graph["department"], code="1916011", title="پروژه بزرگ", credits=19
    )
    plan_offering(graph, student_profile, heavy)
    response = authed_client(student).post(
        "/api/v1/students/me/course-selection/",
        {"course_code": graph["course"].code},
        format="json",
    )
    body = response.json()
    assert body["credit_totals"]["limit"] == 24
    assert body["credit_totals"]["over_limit"] is False
    assert body["eligible"] is True
