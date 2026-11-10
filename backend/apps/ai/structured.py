"""Term-aware structured query service for Phase 09.

Provides deterministic, validated PostgreSQL queries for structured academic
facts (courses, prerequisites, calendars, enrollment) without exposing raw SQL
to the LLM. All queries use Django ORM only.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.academics.models import AcademicTerm
from apps.ai.course_matching import CourseMatch, resolve_course
from apps.calendar.models import AcademicEvent
from apps.common.persian import normalize_persian
from apps.courses.models import ClassSchedule, CourseOffering, CoursePrerequisite
from apps.exams.models import Exam
from apps.students.models import Enrollment, EnrollmentStatus, StudentProfile

logger = logging.getLogger("app.ai.structured")


def _current_term() -> AcademicTerm | None:
    return AcademicTerm.objects.filter(is_current=True).first()


def _find_course(question: str, user=None) -> CourseMatch:
    """Backwards-compatible wrapper for :func:`apps.ai.course_matching.resolve_course`.

    Course-code lookup, containment and word-level matching against the real
    catalog rows, context-aware disambiguation (student field of study,
    prerequisite-graph footprint, offerings, core/elective type) and a
    margin-based ambiguity rule now live in ``course_matching`` so they can
    be reused outside this service.
    """
    return resolve_course(question, user=user)


class StructuredQueryService:
    def answer(self, question: str, user=None) -> dict[str, Any]:
        normalized = normalize_persian(question or "")
        facts: list[dict[str, Any]] = []
        term = _current_term()

        # Resolve the course ONCE per question, using the asking student's
        # context (field of study/faculty) for disambiguation. Ambiguity is
        # reported only when the actual database signals cannot separate the
        # candidates, and no course/answer is invented when nothing matches.
        match = _find_course(question, user=user)
        if match.ambiguous:
            facts.append(
                {
                    "type": "course_ambiguous",
                    "matches": [
                        {"code": c.code, "title": c.title} for c in match.matches[:5]
                    ],
                    "note": (
                        "چند درس مشابه در پایگاه داده پیدا شد که با اطلاعات موجود "
                        "قابل تفکیک نیستند. لطفاً درس مورد نظر را از میان گزینه‌ها "
                        "انتخاب کنید یا کد دقیق درس را بنویسید."
                    ),
                }
            )
        course = match.course

        # Prerequisites for a course — straight from the prerequisite edges.
        if any(k in normalized for k in ("پیش‌نیاز", "پیش نیاز", "پیشنیاز")):
            if course is not None:
                prereqs = CoursePrerequisite.objects.filter(course=course).select_related(
                    "prerequisite_course"
                )
                facts.append(
                    {
                        "type": "prerequisites",
                        "course_code": course.code,
                        "course_title": course.title,
                        "prerequisites": [
                            {
                                "code": p.prerequisite_course.code,
                                "title": p.prerequisite_course.title,
                            }
                            for p in prereqs
                        ],
                    }
                )

        if "امتحان" in normalized:
            if course is not None:
                qs = Exam.objects.select_related("course_offering__course", "course_offering__term")
                if term is not None:
                    qs = qs.filter(course_offering__term=term)
                exam = qs.filter(course_offering__course=course).first()
                if exam is not None:
                    facts.append(
                        {
                            "type": "exam",
                            "course_code": course.code,
                            "course_title": course.title,
                            "term": getattr(exam.course_offering.term, "name", ""),
                            "starts_at": exam.starts_at.isoformat(),
                            "ends_at": exam.ends_at.isoformat(),
                            "classroom": exam.classroom,
                            "status": exam.status,
                        }
                    )

        # Academic calendar / term dates.
        if "ترم" in normalized or "زمان‌بندی" in normalized or "شروع" in normalized:
            if term is not None:
                facts.append(
                    {
                        "type": "academic_calendar",
                        "term_name": term.name,
                        "academic_year": term.academic_year,
                        "semester_type": term.semester_type,
                        "starts_at": term.starts_at.isoformat(),
                        "ends_at": term.ends_at.isoformat(),
                        "is_current": term.is_current,
                    }
                )

        if "استاد" in normalized:
            if course is not None:
                qs = CourseOffering.objects.select_related("professor", "term")
                if term is not None:
                    qs = qs.filter(term=term)
                offering = qs.filter(course=course).first()
                if offering is not None and offering.professor is not None:
                    facts.append(
                        {
                            "type": "professor",
                            "course_code": course.code,
                            "course_title": course.title,
                            "professor": str(offering.professor),
                            "term": getattr(offering.term, "name", ""),
                        }
                    )

        if "واحد" in normalized or "کردیت" in normalized:
            if course is not None:
                facts.append(
                    {
                        "type": "credits",
                        "course_code": course.code,
                        "course_title": course.title,
                        "credits": course.credits,
                    }
                )

        if "ارائه" in normalized or "دروس" in normalized:
            qs = CourseOffering.objects.select_related("course", "term", "professor")
            if term is not None:
                qs = qs.filter(term=term)
            qs = qs[:10]
            for offering in qs:
                facts.append(
                    {
                        "type": "offering",
                        "course_code": offering.course.code,
                        "course_title": offering.course.title,
                        "section": offering.section_code,
                        "status": offering.status,
                        "term": getattr(offering.term, "name", ""),
                    }
                )

        # Student-specific eligibility: can the student register for a course?
        # (normalize_persian strips ZWNJ, so «می‌توانم» == «میتوانم».)
        if user is not None and any(
            k in normalized
            for k in (
                "میتوانم",
                "میتونم",
                "بردارم",
                "مجاز",
            )
        ):
            if course is not None:
                try:
                    profile = StudentProfile.objects.get(user=user)
                except StudentProfile.DoesNotExist:
                    profile = None
                passed_codes: list[str] = []
                if profile is not None:
                    passed = Enrollment.objects.filter(
                        student=profile, status=EnrollmentStatus.PASSED
                    ).select_related("course_offering__course")
                    passed_codes = [e.course_offering.course.code for e in passed]

                # Check prerequisites.
                prereqs = CoursePrerequisite.objects.filter(course=course).select_related(
                    "prerequisite_course"
                )
                missing = [
                    p.prerequisite_course.code
                    for p in prereqs
                    if p.prerequisite_course.code not in passed_codes
                ]
                facts.append(
                    {
                        "type": "eligibility",
                        "course_code": course.code,
                        "course_title": course.title,
                        "passed_courses": passed_codes,
                        "missing_prerequisites": missing,
                        "eligible": len(missing) == 0,
                    }
                )

        # Class schedule for a course offering.
        if "ساعت" in normalized or "برنامه" in normalized or "زمان" in normalized:
            if course is not None:
                qs = (
                    ClassSchedule.objects.select_related(
                        "course_offering__course", "course_offering__term"
                    )
                    .filter(course_offering__course=course)
                )
                if term is not None:
                    qs = qs.filter(course_offering__term=term)
                schedule_list = [
                    {
                        "course_code": s.course_offering.course.code,
                        "course_title": s.course_offering.course.title,
                        "section": s.course_offering.section_code,
                        "weekday": s.get_weekday_display(),
                        "start_time": s.start_time.strftime("%H:%M"),
                        "end_time": s.end_time.strftime("%H:%M"),
                        "classroom": s.classroom,
                        "term": getattr(s.course_offering.term, "name", ""),
                    }
                    for s in qs[:20]
                ]
                facts.append(
                    {
                        "type": "schedule",
                        "schedule": schedule_list,
                    }
                )

        # Academic calendar / events.
        if (
            "تقویم" in normalized
            or "رویداد" in normalized
            or "ثبت‌نام" in normalized
            or "مراسم" in normalized
            or "تعطیل" in normalized
        ):
            qs = AcademicEvent.objects.select_related("term").filter(is_published=True)
            if term is not None:
                qs = qs.filter(term=term)
            event_list = [
                {
                    "title": e.title,
                    "event_type": e.event_type,
                    "starts_at": e.starts_at.isoformat(),
                    "ends_at": e.ends_at.isoformat(),
                    "description": e.description,
                    "term": getattr(e.term, "name", ""),
                }
                for e in qs[:20]
            ]
            facts.append(
                {
                    "type": "calendar",
                    "events": event_list,
                }
            )

        logger.info("structured_query facts=%s", len(facts))
        return {"facts": facts, "term": getattr(term, "name", None)}
