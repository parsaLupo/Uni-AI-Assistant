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
from datetime import datetime, time
from pathlib import Path

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

# Longest-first so «یکشنبه» never matches inside «شنبه».
WEEKDAYS = [
    ("یکشنبه", Weekday.SUNDAY),
    ("دوشنبه", Weekday.MONDAY),
    ("سه‌شنبه", Weekday.TUESDAY),
    ("چهارشنبه", Weekday.WEDNESDAY),
    ("پنجشنبه", Weekday.THURSDAY),
    ("جمعه", Weekday.FRIDAY),
    ("شنبه", Weekday.SATURDAY),
]
_DAY_PATTERN = "|".join(re.escape(name) for name, _ in WEEKDAYS)
_CLASS_RE = re.compile(rf"({_DAY_PATTERN})\s+(\d{{1,2}}:\d{{2}})-(\d{{1,2}}:\d{{2}})")
_CLASSROOM_RE = re.compile(r"مکان\s*:\s*(.+)$")
_EXAM_RE = re.compile(
    r"امتحان\((\d{4})\.(\d{1,2})\.(\d{1,2})\)\s*ساعت\s*:\s*"
    r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})"
)
_WEEKDAY_MAP = dict(WEEKDAYS)

SEMESTER_DATES = {
    # Jalali (start, end) month/day envelopes for one academic year.
    TermSemester.FIRST: ((1, 1), (9, 30)),
    TermSemester.SECOND: ((10, 1), (12, 31)),
    TermSemester.SUMMER: ((4, 1), (6, 31)),
}

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
        pending_edges: list[tuple[str, str]] = []
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
                        pending_edges.append((code, str(rel["related_course_code"])))
        for course_code, prereq_code in pending_edges:
            course = Course.objects.filter(code=course_code).first()
            prereq = Course.objects.filter(code=prereq_code).first()
            if course and prereq and course.pk != prereq.pk:
                _, created = CoursePrerequisite.objects.get_or_create(
                    course=course, prerequisite_course=prereq
                )
                if created:
                    self._bump("prerequisites")

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

    def _professor_index(self) -> dict[str, Professor]:
        return {p.normalized_name: p for p in Professor.objects.all()}

    def _parse_schedule(self, details: list[str], offering: CourseOffering) -> None:
        for line in details:
            exam = _EXAM_RE.search(line)
            if exam:
                jy, jm, jd, sh, sm_, eh, em_ = exam.groups()
                exam_date = jalali_date(int(jy), int(jm), int(jd))
                _, created = Exam.objects.get_or_create(
                    course_offering=offering,
                    defaults={
                        "starts_at": timezone.make_aware(
                            datetime.combine(exam_date, time(int(sh), int(sm_)))
                        ),
                        "ends_at": timezone.make_aware(
                            datetime.combine(exam_date, time(int(eh), int(em_)))
                        ),
                    },
                )
                if created:
                    self._bump("exams")
                continue
            cls = _CLASS_RE.search(line)
            if cls:
                day, start, end = cls.groups()
                room = _CLASSROOM_RE.search(line)
                _, created = ClassSchedule.objects.get_or_create(
                    course_offering=offering,
                    weekday=_WEEKDAY_MAP[day],
                    start_time=time(*map(int, start.split(":"))),
                    end_time=time(*map(int, end.split(":"))),
                    defaults={"classroom": (room.group(1).strip() if room else "")},
                )
                if created:
                    self._bump("schedules")

    def offerings(self, professors: dict[str, Professor]) -> None:
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
                instructor = normalize_persian(str(row.get("instructor_name", "")).strip())
                offering, created = CourseOffering.objects.get_or_create(
                    course=course,
                    term=term,
                    section_code=section or "01",
                    defaults={
                        "professor": professors.get(instructor),
                        "capacity": int(row.get("capacity", 0)),
                        "status": OfferingStatus.OPEN,
                    },
                )
                if created:
                    self._bump("offerings")
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
        self.offerings(self._professor_index())
        self.demo_content()
        self.credentials = self.demo_accounts() if with_demo_accounts else []
        return self.counts



