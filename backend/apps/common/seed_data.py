"""Deterministic, idempotent seeding from the real MVP dataset (V-13, I-13).

Reads `data/*.json` (Semnan University — faculties, departments, courses with
prerequisite relations, professors, and two offering tables whose weekly
schedules and exam dates are embedded Persian strings) and populates a clean
database. Running the command twice is a no-op (get_or_create on business keys).

Demo accounts (guard: DJANGO_DEBUG=true) give terminal/Swagger flows an ADMIN
and a STUDENT identity — closing the Phase 03 gap where privileged roles could
only be created in tests.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.academics.models import AcademicTerm, Department, Faculty, TermSemester
from apps.accounts.models import Role
from apps.common.jalali import jalali_date
from apps.common.persian import normalize_persian
from apps.courses.models import (
    ClassSchedule,
    Course,
    CourseOffering,
    CoursePrerequisite,
    OfferingStatus,
    Weekday,
)
from apps.exams.models import Exam
from apps.professors.models import Professor
from apps.students.models import Enrollment, EnrollmentStatus, StudentProfile

User = get_user_model()

# Canonical Persian weekday labels (presentation; matching uses the flexible
# `_WEEKDAY_PATTERNS` above, so separator/letterform variants never depend on
# this list's order).
WEEKDAYS = [
    ("یکشنبه", Weekday.SUNDAY),
    ("دوشنبه", Weekday.MONDAY),
    ("سه‌شنبه", Weekday.TUESDAY),
    ("چهارشنبه", Weekday.WEDNESDAY),
    ("پنجشنبه", Weekday.THURSDAY),
    ("جمعه", Weekday.FRIDAY),
    ("شنبه", Weekday.SATURDAY),
]

# Source lines mix letterforms and separators: Arabic ي/ك in «يك شنبه»,
# a plain space instead of ZWNJ in «سه شنبه», and the joined «سه‌شنبه».
# Each weekday is a flexible pattern (optional space/ZWNJ between the parts)
# ordered longest-first, so «شنبه» can never win by matching *inside*
# «يك شنبه»/«سه شنبه» — the seed bug that mapped every compound weekday to
# Saturday.
_WEEKDAY_PATTERNS: list[tuple[str, Weekday]] = [
    (r"چهار[ ‌]?شنبه", Weekday.WEDNESDAY),
    (r"پنج[ ‌]?شنبه", Weekday.THURSDAY),
    (r"سه[ ‌]?شنبه", Weekday.TUESDAY),
    (r"[\u06cc\u064a][\u06a9\u0643][ \u200c]?شنبه", Weekday.SUNDAY),
    (r"دو[ ‌]?شنبه", Weekday.MONDAY),
    (r"جمعه", Weekday.FRIDAY),
    (r"شنبه", Weekday.SATURDAY),
]
_DAY_PATTERN = "|".join(f"(?:{pattern})" for pattern, _ in _WEEKDAY_PATTERNS)
_CLASS_RE = re.compile(rf"({_DAY_PATTERN})\s+(\d{{1,2}}:\d{{2}})-(\d{{1,2}}:\d{{2}})")
_CLASSROOM_RE = re.compile(r"مکان\s*:\s*(.+)$")
_EXAM_RE = re.compile(
    r"امتحان\((\d{4})\.(\d{1,2})\.(\d{1,2})\)\s*ساعت\s*:\s*"
    r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})"
)
# jalali weekday label per Weekday value (presentation only).
_WEEKDAY_LABELS: dict[Weekday, str] = {
    weekday: name for name, weekday in WEEKDAYS
}

def _weekday_of(day_text: str) -> Weekday:
    """Canonical Weekday for a matched day name (any letterform/separator)."""
    for pattern, weekday in _WEEKDAY_PATTERNS:
        if re.fullmatch(pattern, day_text):
            return weekday
    raise ValueError(f"unknown weekday: {day_text!r}")


def parse_class_session(line: str) -> tuple[Weekday, time, time, str] | None:
    """Parse «درس(ت): شنبه 12:00-15:00 مکان: ...» → (weekday, start, end, room).

    Returns None for lines that are not weekly class sessions (exam lines,
    continuation-row references, anything else).
    """
    match = _CLASS_RE.search(line)
    if match is None:
        return None
    day, start, end = match.groups()
    room = _CLASSROOM_RE.search(line)
    return (
        _weekday_of(day),
        time(*map(int, start.split(":"))),
        time(*map(int, end.split(":"))),
        room.group(1).strip() if room else "",
    )


def parse_exam_slot(line: str) -> tuple[date, time, time, str] | None:
    """Parse «امتحان(1405.10.20) ساعت : 16:00-18:00» → (date, start, end, room).

    The Jalali date converts via the project's `jalali_date`; the room stays
    empty because exam rows in the dataset carry no «مکان». Returns None for
    non-exam lines (class sessions must never be read as exam dates).
    """
    match = _EXAM_RE.search(line)
    if match is None:
        return None
    jy, jm, jd, sh, sm_, eh, em_ = match.groups()
    room = _CLASSROOM_RE.search(line)
    return (
        jalali_date(int(jy), int(jm), int(jd)),
        time(int(sh), int(sm_)),
        time(int(eh), int(em_)),
        room.group(1).strip() if room else "",
    )


SEMESTER_DATES = {
    # Jalali (start, end) month/day envelopes for one academic year.
    TermSemester.FIRST: ((1, 1), (9, 30)),
    TermSemester.SECOND: ((10, 1), (12, 31)),
    TermSemester.SUMMER: ((4, 1), (6, 31)),
}

# The dataset's wall-clock times are Iran local time (Asia/Tehran, +03:30).
# `timezone.make_aware` with the default (UTC, per settings.TIME_ZONE) would
# store the announced 10:00 exam as 10:00 UTC — 3:30 hours off for viewers in
# Tehran — so every parsed exam instant is pinned to the Iran zone instead.
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

DEMO_PASSWORD = "Demo-Passw0rd!"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class Seeder:
    def __init__(self, data_dir: Path, stdout):
        self.data_dir = data_dir
        self.stdout = stdout
        self.counts: dict[str, int] = {}
        self.credentials: list[str] = []

    def _bump(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def faculties(self) -> dict[str, Faculty]:
        result: dict[str, Faculty] = {}
        for row in _load(self.data_dir / "Faculty.json")["faculty"]:
            code = str(row["id"])
            faculty, created = Faculty.objects.get_or_create(
                code=code,
                defaults={
                    "name": row["name"],
                    "website": row.get("website", ""),
                    "description": row.get("description", ""),
                },
            )
            if created:
                self._bump("faculties")
            result[code] = faculty
        return result

    def departments(self, faculties: dict[str, Faculty]) -> dict[str, Department]:
        result: dict[str, Department] = {}
        for row in _load(self.data_dir / "departments.json")["departments"]:
            code = str(row["code"])
            faculty = faculties.get(str(row["faculty_code"]))
            if faculty is None:
                continue
            department, created = Department.objects.get_or_create(
                faculty=faculty,
                code=code,
                defaults={"name": row["name"], "description": row.get("description", "")},
            )
            if created:
                self._bump("departments")
            result[code] = department
        return result

    def courses(self, departments: dict[str, Department]) -> None:
        # Official per-cohort prerequisite rules: the sources repeat an edge
        # once per entry-term cohort (curriculum revision), e.g. 1916020
        # requires 1916008 for cohorts 3941/3951 but 1916228 for 4011/4021.
        # The (course, prerequisite) pair stays unique; the cohort codes are
        # stored on the edge so the selection engine can resolve the student's
        # applicable rule set (see course_selection.py).
        pending_edges: dict[tuple[str, str], set[str]] = {}
        for filename in ("courses.json", "course2.json"):
            path = self.data_dir / filename
            if not path.exists():
                continue
            for row in _load(path)["courses"]:
                code = str(row["code"])
                # Codes embed faculty+department (19 16 001); the raw
                # department_code field is unreliable ("COMPUTER" vs "16").
                department = departments.get(code[2:4]) or departments.get(
                    str(row.get("department_code", ""))
                )
                if department is None:
                    continue
                _, created = Course.objects.get_or_create(
                    code=code,
                    defaults={
                        "department": department,
                        "title": row["title"],
                        "credits": int(row.get("credits", 0)),
                        "course_type": str(row.get("course_type", "")).strip(),
                    },
                )
                if created:
                    self._bump("courses")
                for rel in row.get("relations", []):
                    if rel.get("type") == "prerequisite" and rel.get("related_course_code"):
                        key = (code, str(rel["related_course_code"]))
                        entry_term = str(rel.get("entry_term") or "").strip()
                        pending_edges.setdefault(key, set())
                        if entry_term:
                            pending_edges[key].add(entry_term)
        for (course_code, prereq_code), cohort_terms in sorted(pending_edges.items()):
            course = Course.objects.filter(code=course_code).first()
            prereq = Course.objects.filter(code=prereq_code).first()
            if course and prereq and course.pk != prereq.pk:
                edge, created = CoursePrerequisite.objects.get_or_create(
                    course=course,
                    prerequisite_course=prereq,
                    defaults={"entry_terms": sorted(cohort_terms)},
                )
                if created:
                    self._bump("prerequisites")
                else:
                    # Backfill cohorts on edges seeded before this metadata
                    # existed; merge, never overwrite valid history.
                    merged = sorted({*edge.entry_terms, *cohort_terms})
                    if merged != edge.entry_terms:
                        edge.entry_terms = merged
                        edge.save(update_fields=["entry_terms"])

    def professors(self, departments: dict[str, Department]) -> None:
        path = self.data_dir / "Professors.json"
        if not path.exists():
            return
        for row in _load(path)["professors"]:
            department = departments.get(str(row["department_code"]))
            if department is None:
                continue
            email = str(row.get("email", "")).strip()
            _, created = Professor.objects.get_or_create(
                department=department,
                first_name=str(row["first_name"]).strip(),
                last_name=str(row["last_name"]).strip(),
                defaults={
                    "academic_title": str(row.get("academic_rank", "")).strip(),
                    "email": email if "@" in email else "",
                    "website": str(row.get("website", "")).strip(),
                },
            )
            if created:
                self._bump("professors")

    # --- offerings, schedules, exams ----------------------------------------
    def _term(self, academic_year: str, semester: str) -> AcademicTerm:
        semester_type = TermSemester(semester)
        year = int(academic_year.split("-")[0])
        (sm, sd), (em, ed) = SEMESTER_DATES[semester_type]
        no_current = not AcademicTerm.objects.filter(is_current=True).exists()
        term, created = AcademicTerm.objects.get_or_create(
            academic_year=academic_year,
            semester_type=semester_type,
            defaults={
                "name": f"{semester_type.label} {academic_year}",
                "starts_at": jalali_date(year, sm, sd),
                "ends_at": jalali_date(year, em, ed),
                "is_current": no_current,
            },
        )
        if created:
            self._bump("terms")
        return term

    def _professor_index(
        self,
    ) -> tuple[dict[str, Professor], dict[str, list[Professor]]]:
        """Roster indexes for matching `instructor_name` strings: by the
        normalized full name (roster order: given + family) and by the
        normalized family name (the offering tables write the family name
        first, the roster's `normalized_name` writes it second)."""
        by_full: dict[str, Professor] = {}
        by_family: dict[str, list[Professor]] = {}
        for professor in Professor.objects.all():
            by_full[professor.normalized_name] = professor
            by_family.setdefault(
                normalize_persian(professor.last_name), []
            ).append(professor)
        return by_full, by_family

    def _resolve_professor(
        self,
        roster: tuple[dict[str, Professor], dict[str, list[Professor]]],
        departments: dict[str, Department],
        department_code: str,
        instructor_name: str,
    ) -> Professor | None:
        """Match «نام خانوادگی نام» from the offering tables to a Professor.

        Matching never trusts a single spelling: both sides go through
        `normalize_persian` (Arabic ي/ك → Persian ی/ک), the roster is searched
        by full name and then by family name, and only then does an unknown
        instructor become their own Professor row in the offering's
        department. The name convention follows the roster itself: the given
        name is the LAST token («فدائي اسلام محمدجواد» → first «محمدجواد»,
        last «فدائی اسلام» per Professors.json). Group placeholders
        («اساتيد گروه آموزشي») are not people and never become professors.
        """
        name = instructor_name.strip()
        if not name:
            return None
        by_full, by_family = roster
        exact = by_full.get(normalize_persian(name))
        if exact is not None:
            return exact
        family, _, given = name.rpartition(" ")
        family_n = normalize_persian(family)
        given_n = normalize_persian(given or family)
        if "گروه" in family_n or "گروه" in given_n:
            return None
        candidates = by_family.get(family_n, [])
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            for candidate in candidates:
                if normalize_persian(candidate.first_name) == given_n:
                    return candidate
            department = departments.get(str(department_code))
            if department is not None:
                for candidate in candidates:
                    if candidate.department_id == department.id:
                        return candidate
            return None
        department = departments.get(str(department_code))
        if department is None:
            return None
        professor, _ = Professor.objects.get_or_create(
            department=department,
            first_name=(given or family).strip(),
            last_name=(family or given).strip(),
        )
        # Cache so sibling rows of the same instructor reuse this Professor
        # (and the next seed run matches through the roster indexes).
        by_full[normalize_persian(name)] = professor
        by_family.setdefault(family_n, []).append(professor)
        self._bump("professors")
        return professor

    def _parse_schedule(self, details: list[str], offering: CourseOffering) -> None:
        """Import one offering's schedule/exam lines.

        `schedule_details` already carries the merged continuation rows, and
        every parse goes through `get_or_create`, so re-importing (or the same
        session listed twice across rows) can never duplicate a fact.
        """
        for line in details:
            exam = parse_exam_slot(line)
            if exam is not None:
                exam_date, starts, ends, classroom = exam
                # Source times are Tehran wall-clock; pin the zone (see
                # TEHRAN_TZ) so the stored instant matches the announced time.
                _, created = Exam.objects.get_or_create(
                    course_offering=offering,
                    defaults={
                        "starts_at": timezone.make_aware(
                            datetime.combine(exam_date, starts), TEHRAN_TZ
                        ),
                        "ends_at": timezone.make_aware(
                            datetime.combine(exam_date, ends), TEHRAN_TZ
                        ),
                        "classroom": classroom,
                    },
                )
                if created:
                    self._bump("exams")
                continue
            session = parse_class_session(line)
            if session is not None:
                weekday, start, end, classroom = session
                _, created = ClassSchedule.objects.get_or_create(
                    course_offering=offering,
                    weekday=weekday,
                    start_time=start,
                    end_time=end,
                    defaults={"classroom": classroom},
                )
                if created:
                    self._bump("schedules")

    def offerings(
        self,
        roster: tuple[dict[str, Professor], dict[str, list[Professor]]],
        departments: dict[str, Department],
    ) -> None:
        for filename in ("course-offering.json", "course-offering2.json"):
            path = self.data_dir / filename
            if not path.exists():
                continue
            payload = _load(path)
            term = self._term(payload["academic_year"], payload["semester"])
            for row in payload["courses"]:
                group = str(row["course_group_code"])
                code, _, section = group.partition("_")
                course = Course.objects.filter(code=code).first()
                if course is None:
                    continue
                professor = self._resolve_professor(
                    roster,
                    departments,
                    str(row.get("department_code", "")),
                    str(row.get("instructor_name", "")),
                )
                offering, created = CourseOffering.objects.get_or_create(
                    course=course,
                    term=term,
                    section_code=section or "01",
                    defaults={
                        "professor": professor,
                        "capacity": int(row.get("capacity", 0)),
                        "status": OfferingStatus.OPEN,
                    },
                )
                if created:
                    self._bump("offerings")
                elif offering.professor_id is None and professor is not None:
                    # Backfill: offerings seeded before instructor matching
                    # existed get their professor without a recreate cycle.
                    offering.professor = professor
                    offering.save(update_fields=["professor"])
                self._parse_schedule(row.get("schedule_details", []), offering)

    # --- demo content & accounts --------------------------------------------
    def demo_content(self) -> None:
        """Persian announcements/events for the current term (demo realism)."""
        from apps.announcements.models import Announcement, AnnouncementPriority
        from apps.calendar.models import AcademicEvent, EventType

        current = AcademicTerm.objects.filter(is_current=True).first()
        if current is None:
            return
        now = timezone.now()
        _, created = Announcement.objects.get_or_create(
            title="برنامه ثبت‌نام نیمسال جاری اعلام شد",
            defaults={
                "term": current,
                "body": (
                    "ثبت‌نام دروس از تاریخ اعلام‌شده در سامانه آغاز می‌شود؛ "
                    "پیش از انتخاب درس، پیش‌نیازها و سقف واحد را بررسی کنید."
                ),
                "priority": AnnouncementPriority.HIGH,
                "is_published": True,
                "published_at": now,
            },
        )
        if created:
            self._bump("announcements")
        _, created = AcademicEvent.objects.get_or_create(
            term=current,
            title="پنجره ثبت‌نام نیمسال",
            defaults={
                "event_type": EventType.REGISTRATION,
                "starts_at": timezone.make_aware(
                    datetime.combine(current.starts_at, time(8, 0))
                ),
                "ends_at": timezone.make_aware(
                    datetime.combine(current.starts_at, time(23, 59))
                ),
                "description": "بازه انتخاب واحد نیمسال جاری",
                "is_published": True,
            },
        )
        if created:
            self._bump("events")

    def demo_accounts(self) -> list[str]:
        """Development identities for terminal/Swagger flows (non-production)."""
        if not settings.DEBUG:
            return []
        lines: list[str] = []
        specs = [
            ("root@semnan.local", Role.SUPERADMIN, "مدیر ارشد", "آزمایشی"),
            ("admin@semnan.local", Role.ADMIN, "مدیر", "آزمایشی"),
            (
                "student@semnan.local",
                Role.STUDENT,
                "سارا",
                "محمدی",
            ),
        ]
        for spec in specs:
            email, role, first, last = spec[0], spec[1], spec[2], spec[3] if len(spec) > 3 else ""
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last or "",
                    "role": role,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
                self._bump("demo_accounts")
            if role == Role.STUDENT:
                department = Department.objects.filter(code="16").first()
                profile, _ = StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "student_number": "40411234",
                        "department": department,
                        "faculty": department.faculty if department else None,
                        "degree_level": "BACHELOR",
                        "entry_year": "1403",
                    },
                )
                # Two planner rows so the planner screen has content.
                term = AcademicTerm.objects.filter(is_current=True).first()
                if term is not None:
                    for offering in CourseOffering.objects.filter(term=term)[:2]:
                        Enrollment.objects.get_or_create(
                            student=profile,
                            course_offering=offering,
                            defaults={"status": EnrollmentStatus.PLANNED},
                        )
            lines.append(f"  {role:<11} {email}  /  {DEMO_PASSWORD}")
        return lines

    # --- orchestration -------------------------------------------------------
    @transaction.atomic
    def run(self, *, with_demo_accounts: bool = True) -> dict[str, int]:
        missing = [
            name
            for name in ("Faculty.json", "departments.json", "courses.json")
            if not (self.data_dir / name).exists()
        ]
        if missing:
            raise FileNotFoundError(f"data directory missing files: {missing}")
        faculties = self.faculties()
        departments = self.departments(faculties)
        self.courses(departments)
        self.professors(departments)
        self.offerings(self._professor_index(), departments)
        self.demo_content()
        self.credentials = self.demo_accounts() if with_demo_accounts else []
        return self.counts



