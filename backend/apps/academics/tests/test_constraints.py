"""V-14 database constraints — each test attempts the violation itself."""

from __future__ import annotations

from datetime import date, time

import pytest
from django.db import IntegrityError, transaction

from apps.academics.models import AcademicTerm, Department
from apps.courses.models import ClassSchedule, Course, CourseOffering, CoursePrerequisite

pytestmark = pytest.mark.django_db


def _term(year: int, *, current: bool = False) -> AcademicTerm:
    # Jalali year + 621 ≈ Gregorian year for the Mar-start of an academic year.
    return AcademicTerm.objects.create(
        name=f"ترم {year}",
        academic_year=f"{year}-{year + 1}",
        semester_type="FIRST",
        starts_at=date(year + 621, 3, 21),
        ends_at=date(year + 622, 1, 9),
        is_current=current,
    )


def test_at_most_one_current_term():
    _term(1404, current=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        _term(1405, current=True)


def test_term_start_before_end_check():
    with pytest.raises(IntegrityError), transaction.atomic():
        AcademicTerm.objects.create(
            name="ترم معکوس",
            academic_year="1405-1406",
            semester_type="FIRST",
            starts_at=date(2027, 1, 1),
            ends_at=date(2026, 1, 1),
        )


def test_department_code_unique_per_faculty(academic_graph):
    with pytest.raises(IntegrityError), transaction.atomic():
        Department.objects.create(
            faculty=academic_graph["faculty"], name="گروه تکراری", code="16"
        )


def test_course_code_unique_globally(academic_graph):
    other = Department.objects.create(
        faculty=academic_graph["faculty"], name="گروه دیگر", code="99"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Course.objects.create(
            department=other, code="1916001", title="کد تکراری", credits=2
        )


def test_one_section_per_course_per_term(academic_graph):
    CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        CourseOffering.objects.create(
            course=academic_graph["course"],
            term=academic_graph["term"],
            section_code="01",
        )


def test_no_self_prerequisite(academic_graph):
    with pytest.raises(IntegrityError), transaction.atomic():
        CoursePrerequisite.objects.create(
            course=academic_graph["course"],
            prerequisite_course=academic_graph["course"],
        )


def test_schedule_start_before_end(academic_graph):
    offering = CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ClassSchedule.objects.create(
            course_offering=offering, weekday=5,
            start_time=time(14, 0), end_time=time(12, 0),
        )


def test_one_exam_per_offering_is_one_to_one(academic_graph):
    from django.utils import timezone

    from apps.exams.models import Exam

    offering = CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )
    Exam.objects.create(
        course_offering=offering,
        starts_at=timezone.now(),
        ends_at=timezone.now() + timezone.timedelta(hours=2),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Exam.objects.create(
            course_offering=offering,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timezone.timedelta(hours=2),
        )


def test_enrollment_unique_per_student_offering(student_profile, academic_graph):
    from apps.students.models import Enrollment

    offering = CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], section_code="01"
    )
    Enrollment.objects.create(student=student_profile, course_offering=offering)
    with pytest.raises(IntegrityError), transaction.atomic():
        Enrollment.objects.create(student=student_profile, course_offering=offering)
