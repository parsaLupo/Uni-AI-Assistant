"""Seed command contract (V-13): imports the real dataset, idempotent, guarded."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.academics.models import Department
from apps.common.seed_data import Seeder
from apps.courses.models import ClassSchedule, Course, CourseOffering, CoursePrerequisite, Weekday
from apps.exams.models import Exam
from apps.professors.models import Professor

pytestmark = pytest.mark.django_db

DATA_DIR = Path(settings.BASE_DIR).parent / "data"


def test_seed_imports_the_real_dataset_and_is_idempotent():
    call_command("seed", data_dir=str(DATA_DIR))
    courses = Course.objects.count()
    offerings = CourseOffering.objects.count()
    prerequisites = CoursePrerequisite.objects.count()
    schedules = ClassSchedule.objects.count()
    exams = Exam.objects.count()
    assert courses > 100, "the dataset carries 1100+ courses"
    assert offerings > 100
    assert prerequisites > 100, "prerequisite relations must survive import"
    assert schedules > 100, "weekly rows parsed from Persian schedule strings"
    assert exams > 50, "exam dates parsed from «امتحان(1405.10.20)» strings"

    # Second run: nothing created.
    call_command("seed", data_dir=str(DATA_DIR))
    assert Course.objects.count() == courses
    assert CourseOffering.objects.count() == offerings
    assert ClassSchedule.objects.count() == schedules
    assert Exam.objects.count() == exams


def test_seed_refuses_outside_development(settings):
    settings.DEBUG = False
    settings.IS_TESTS = False  # the test-run bypass itself must not mask the guard
    with pytest.raises(CommandError, match="refuses to run outside development"):
        call_command("seed", data_dir=str(DATA_DIR))


def test_seed_without_data_dir_fails_loudly(tmp_path):
    with pytest.raises(CommandError, match="data directory not found"):
        call_command("seed", data_dir=str(tmp_path / "nope"))


def _source_details_for(group_code: str) -> list[str]:
    """The real `schedule_details` lines for one offering group from the JSONs."""
    for filename in ("course-offering.json", "course-offering2.json"):
        payload = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
        for row in payload["courses"]:
            if str(row["course_group_code"]) == group_code:
                return row.get("schedule_details", [])
    raise AssertionError(f"{group_code} not found in the source data")


def _offering_for(group_code: str) -> CourseOffering:
    """The seeded offering (with parsed schedules) for a group code like
    «1916219_01». If the code+section appears in both source files, the one
    that actually carries schedule rows is the one under test."""
    code, _, section = group_code.partition("_")
    offerings = CourseOffering.objects.filter(
        course__code=code, section_code=section or "01"
    )
    for offering in offerings:
        if offering.schedules.exists():
            return offering
    raise AssertionError(f"{group_code} was not seeded with schedule rows")


def test_seed_parses_compound_weekdays_and_multiple_weekly_sessions():
    call_command("seed", data_dir=str(DATA_DIR))
    # 1916219_01 meets twice weekly: یکشنبه 10-12 AND سه‌شنبه 13-14 in the
    # source; both rows must exist and neither may be (wrongly) Saturday.
    offering = _offering_for("1916219_01")
    rows = list(
        ClassSchedule.objects.filter(course_offering=offering).order_by("start_time")
    )
    # Both weekly sessions of the source, with the correct compound weekdays
    # (neither may fall back to Saturday).
    assert [
        (r.weekday, r.start_time.strftime("%H:%M"), r.end_time.strftime("%H:%M"))
        for r in rows
    ] == [
        (Weekday.SUNDAY, "10:00", "12:00"),
        (Weekday.TUESDAY, "13:00", "14:00"),
    ]


def test_reparse_of_the_same_details_never_duplicates_rows():
    call_command("seed", data_dir=str(DATA_DIR))
    offering = _offering_for("1916219_01")
    details = _source_details_for("1916219_01")
    seeder = Seeder(DATA_DIR, None)
    schedules_before = ClassSchedule.objects.filter(course_offering=offering).count()
    exams_before = Exam.objects.filter(course_offering=offering).count()
    seeder._parse_schedule(details, offering)
    seeder._parse_schedule(details, offering)
    assert ClassSchedule.objects.filter(course_offering=offering).count() == schedules_before
    assert Exam.objects.filter(course_offering=offering).count() == exams_before


def test_offering_without_exam_line_gets_no_exam_row():
    call_command("seed", data_dir=str(DATA_DIR))
    # 1916021_01 announces no exam date in the source — the honest state is
    # "no Exam row" (the UI shows «تاریخ امتحان اعلام نشده است»), never an
    # inferred date.
    offering = _offering_for("1916021_01")
    assert not Exam.objects.filter(course_offering=offering).exists()
    seeder = Seeder(DATA_DIR, None)
    seeder._parse_schedule(_source_details_for("1916021_01"), offering)
    assert not Exam.objects.filter(course_offering=offering).exists()
    # Its weekly session IS parsed: سه‌شنبه 08:00-10:00.
    rows = ClassSchedule.objects.filter(course_offering=offering)
    assert [(r.weekday, r.start_time.strftime("%H:%M")) for r in rows] == [
        (Weekday.TUESDAY, "08:00")
    ]


def test_seed_attaches_instructor_names_as_professors():
    call_command("seed", data_dir=str(DATA_DIR))
    # Roster match: «رحماني منش محمد» is the imported «محمد رحمانی منش» —
    # the same Professor row keeps its academic rank (no duplicate created).
    security = _offering_for("1916219_01")
    assert security.professor is not None
    assert security.professor.first_name == "محمد"
    assert security.professor.last_name == "رحمانی منش"
    assert security.professor.academic_title == "دانشیار"
    # Unknown instructors become their own Professor row in the offering's
    # department; «نام خانوادگی نام» → family first, given last.
    lab = _offering_for("1916021_01")
    assert lab.professor is not None
    assert (lab.professor.first_name, lab.professor.last_name) == ("فاطمه", "ارغوان")
    dept16 = Department.objects.filter(code="16").first()
    assert dept16 is not None
    assert lab.professor.department_id == dept16.id
    # The «اساتيد گروه آموزشي» placeholder is not a person.
    placeholder = CourseOffering.objects.filter(
        course__code="1916148", section_code="01"
    ).first()
    assert placeholder is not None and placeholder.professor is None
    # Idempotent: a second run neither adds nor renames professors.
    professors = Professor.objects.count()
    call_command("seed", data_dir=str(DATA_DIR))
    assert Professor.objects.count() == professors


def test_resolve_professor_roster_match_and_creation():
    call_command("seed", data_dir=str(DATA_DIR))
    seeder = Seeder(DATA_DIR, None)
    roster = seeder._professor_index()
    departments = seeder.departments(seeder.faculties())
    before = Professor.objects.count()
    # Multi-part family name matches the roster row exactly (given name is
    # the LAST token of the instructor string).
    matched = seeder._resolve_professor(
        roster, departments, "16", "فدائي اسلام محمدجواد"
    )
    assert matched is not None
    assert (matched.first_name, matched.last_name) == ("محمدجواد", "فدائی اسلام")
    assert Professor.objects.count() == before
    # An instructor missing from the roster is created once, in dept 16.
    created = seeder._resolve_professor(
        roster, departments, "16", "تست زاده تجربي"
    )
    assert created is not None
    assert (created.first_name, created.last_name) == ("تجربي", "تست زاده")
    assert created.department_id == departments["16"].id
    assert Professor.objects.count() == before + 1
    # The same name resolves to the same Professor (no duplicates), and the
    # placeholder never becomes one.
    again = seeder._resolve_professor(roster, departments, "16", "تست زاده تجربي")
    assert again is not None and again.id == created.id
    assert Professor.objects.count() == before + 1
    assert (
        seeder._resolve_professor(roster, departments, "16", "اساتيد گروه آموزشي")
        is None
    )
    assert seeder._resolve_professor(roster, departments, "16", "") is None
