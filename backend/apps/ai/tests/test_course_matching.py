"""Course-name recognition + prerequisite retrieval tests (root-cause fix).

Regression coverage for the bug where «pish-niaz» questions about
«نظریه زبان‌ها و ماشین‌ها» or «سیستم عامل» fell through to "insufficient
evidence" or demanded a course code even though the catalog uniquely (or
contextually) identifies the course.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.academics.models import Department, Faculty
from apps.ai.answer import AnswerService
from apps.ai.course_matching import resolve_course
from apps.ai.formatter import INSUFFICIENT_EVIDENCE_MESSAGE
from apps.ai.modes import ExecutionMode
from apps.ai.providers import MockLLMProvider
from apps.ai.structured import StructuredQueryService
from apps.courses.models import Course, CoursePrerequisite


def _course(department, code: str, title: str, course_type: str = "") -> Course:
    return Course.objects.create(
        department=department,
        code=code,
        title=title,
        credits=3,
        course_type=course_type,
    )


def _edge(course: Course, prerequisite: Course) -> None:
    CoursePrerequisite.objects.create(course=course, prerequisite_course=prerequisite)


class CatalogFixtureMixin:
    """Catalog shaped like the real seed: duplicate catalog titles across
    curriculum versions, with prerequisite-graph activity separating them."""

    @classmethod
    def setUpTestData(cls):
        cls.faculty_cs = Faculty.objects.create(
            name="دانشکده مهندسی کامپیوتر", code="F-CE"
        )
        cls.department_cs = Department.objects.create(
            faculty=cls.faculty_cs, name="گروه مهندسی کامپیوتر", code="16"
        )
        cls.faculty_ee = Faculty.objects.create(name="دانشکده مهندسی برق", code="F-EE")
        cls.department_ee = Department.objects.create(
            faculty=cls.faculty_ee, name="گروه مهندسی برق", code="17"
        )
        cls._seed_curriculum_variants()
        cls._seed_operating_systems()
        cls.service = StructuredQueryService()

    @classmethod
    def _seed_curriculum_variants(cls):
        """Three catalog rows named «نظریه زبان‌ها و ماشین‌ها» (real 1916008,
        1916228, 1916354 pattern) — the main variant is the most connected."""
        cls.course_data_structures = _course(
            cls.department_cs, "1916006", "ساختمانهای داده", "اصلی"
        )
        cls.compiler = _course(cls.department_cs, "1916109", "کامپایلر", "اصلی")
        cls.theory_main = _course(
            cls.department_cs, "1916008", "نظریه زبان ها و ماشین ها", "اصلی"
        )
        cls.theory_alt = _course(
            cls.department_cs, "1916228", "نظریه زبانها و ماشین ها", "اصلی"
        )
        cls.theory_specialized = _course(
            cls.department_cs, "1916354", "نظریه زبان ها و ماشین ها", "تخصصی"
        )
        _edge(cls.theory_main, cls.course_data_structures)  # out 1
        _edge(cls.compiler, cls.theory_main)  # in 1 …
        cls.os_theory_course = _course(
            cls.department_cs, "1916027", "انتقال داده ها", "تخصصی"
        )
        _edge(cls.os_theory_course, cls.theory_main)  # … in 2
        _edge(cls.theory_alt, _course(cls.department_cs, "1916208", "مبانی نظریه", "تخصصی"))
        _edge(cls.theory_specialized, _course(cls.department_cs, "1916350", "ارتباط داده ها", "تخصصی"))

    @classmethod
    def _seed_operating_systems(cls):
        cls.computer_architecture = _course(
            cls.department_cs, "1916012", "معماری کامپیوتر", "اصلی"
        )
        cls.os_main = _course(
            cls.department_cs, "1916013", "سیستم های عامل", "اصلی"
        )
        cls.os_specialized = _course(
            cls.department_cs, "1916358", "سیستم های عامل", "تخصصی"
        )
        cls.os_lab = _course(
            cls.department_cs, "1916021", "آزمایشگاه سیستم های عامل", "اصلی"
        )
        cls.os_specialized_lab = _course(
            cls.department_cs, "1916359", "آزمایشگاه سیستم های عامل", "تخصصی"
        )
        cls.os_advanced = _course(
            cls.department_cs, "1916150", "سیستم های عامل پیشرفته", "الزامی"
        )
        cls.os_advanced_elective = _course(
            cls.department_cs, "1916278", "سیستم عامل پیشرفته", "اختیاری"
        )
        _edge(cls.os_main, cls.computer_architecture)
        _edge(cls.os_main, cls.course_data_structures)
        _edge(cls.os_specialized, _course(cls.department_cs, "1916351", "کارآموزی", "تخصصی"))
        _edge(cls.os_specialized, _course(cls.department_cs, "1916499", "پایان نامه", "تخصصی"))
        _edge(cls.os_lab, cls.os_main)
        _edge(cls.os_specialized_lab, cls.os_specialized)
        _edge(_course(cls.department_cs, "1916165", "کامپایلر پیشرفته", "اصلی"), cls.os_main)


class IdentifyCourseByNameTests(CatalogFixtureMixin, TestCase):
    def test_theory_of_languages_resolves_without_course_code(self):
        result = self.service.answer("پیش‌نیاز درس نظریه‌زبان‌ها و ماشین‌ها چیست؟")
        self.assertNotIn(
            "course_ambiguous", [fact["type"] for fact in result["facts"]]
        )
        self.assertEqual(len(result["facts"]), 1)
        fact = result["facts"][0]
        self.assertEqual(fact["type"], "prerequisites")
        self.assertEqual(fact["course_code"], "1916008")
        self.assertEqual(fact["course_title"], "نظریه زبان ها و ماشین ها")
        self.assertEqual({p["code"] for p in fact["prerequisites"]}, {"1916006"})

    def test_operating_systems_resolves_core_variant(self):
        """«سیستم عامل» vs catalog rows «سیستم های عامل» (core + specialized)
        and «سیستم عامل پیشرفته» — the core course must win without asking
        for a code."""
        result = self.service.answer("پیش نیاز درس سیستم عامل چیست؟")
        self.assertEqual(len(result["facts"]), 1)
        fact = result["facts"][0]
        self.assertEqual(fact["type"], "prerequisites")
        self.assertEqual(fact["course_code"], "1916013")
        self.assertEqual({p["code"] for p in fact["prerequisites"]}, {"1916012", "1916006"})

    def test_operating_system_advanced_resolves_variant(self):
        result = self.service.answer("پیش نیاز درس سیستم عامل پیشرفته چیست؟")
        self.assertEqual(len(result["facts"]), 1)
        fact = result["facts"][0]
        self.assertEqual(fact["course_code"], "1916150")
        self.assertEqual(fact["prerequisites"], [])

    def test_lab_course_wins_when_fuller_name_is_typed(self):
        match = resolve_course("پیش نیاز آزمایشگاه سیستم عامل چیست؟")
        self.assertFalse(match.ambiguous)
        self.assertEqual(match.course.code, "1916021")

    def test_course_code_beats_name_guesses(self):
        match = resolve_course("گروه 1916013_02 سیستم عامل")
        self.assertFalse(match.ambiguous)
        self.assertEqual(match.course.code, "1916013")


class PersianVariantMatchingTests(CatalogFixtureMixin, TestCase):
    def test_zwnj_space_and_letter_variants(self):
        cases = {
            # plain spaces
            "پیش نیاز درس نظریه زبان ها و ماشین ها چیست؟": "1916008",
            # ZWNJ instead of spaces inside the name
            "پیش‌نیاز نظریه‌زبان‌هاوماشین‌ها چیست": "1916008",
            # Arabic yeh (ي/ى) forms and non-spaced plural
            "پیش نیاز نظريه زبانها و ماشين ها؟": "1916008",
            # Arabic kaf + yeh in «سيستم هاي عامل»
            "پیش نیاز درس سيستم هاي عامل چیست": "1916013",
            # Persian digits inside the course code
            "پیش نیاز درس ۱۹۱۶۰۱۳ چیست": "1916013",
        }
        for question, expected_code in cases.items():
            with self.subTest(question=question):
                match = resolve_course(question)
                self.assertFalse(match.ambiguous, msg=question)
                self.assertIsNotNone(match.course, msg=question)
                self.assertEqual(match.course.code, expected_code, msg=question)

    def test_minor_typo_still_matches(self):
        # «ساختمان» instead of the seeded «ساختمانهای داده» (h missing)
        match = resolve_course("پیش نیاز درس ساختمان های داده چیست؟")
        self.assertFalse(match.ambiguous)
        self.assertEqual(match.course.code, "1916006")


class PrerequisiteRetrievalTests(CatalogFixtureMixin, TestCase):
    def test_end_to_end_answer_not_insufficient(self):
        provider = MockLLMProvider(response_text="پاسخ")
        result = AnswerService(provider=provider).answer(
            "پیش‌نیاز درس سیستم عامل چیست؟"
        )
        self.assertEqual(result["mode"], ExecutionMode.STRUCTURED.value)
        self.assertFalse(result["insufficient_evidence"])
        self.assertNotEqual(result["answer"], INSUFFICIENT_EVIDENCE_MESSAGE)
        self.assertTrue(result["structured_evidence"])
        self.assertEqual(
            result["structured_evidence"][0]["course_code"], "1916013"
        )

    def test_no_course_invented_when_no_match(self):
        result = self.service.answer("پیش نیاز درس فیزیک کوانتوم چیست؟")
        self.assertEqual(result["facts"], [])


class AmbiguityBehaviourTests(CatalogFixtureMixin, TestCase):
    def test_genuine_tie_asks_for_clarification(self):
        """Symmetric duplicates (same title, same signals) are the ONLY case
        that may ask the user which course they meant."""
        base = _course(self.department_cs, "2001", "پایگاه داده ها", "تخصصی")
        twin = _course(self.department_cs, "2002", "پایگاه داده ها", "تخصصی")
        _edge(base, _course(self.department_cs, "9001", "مبانی برنامه سازی", "تخصصی"))
        _edge(_course(self.department_cs, "9002", "هوش مصنوعی", "اصلی"), base)
        _edge(twin, _course(self.department_cs, "9003", "مبانی برنامه سازی", "تخصصی"))
        _edge(_course(self.department_cs, "9004", "هوش مصنوعی", "اصلی"), twin)

        result = self.service.answer("پیش نیاز درس پایگاه داده ها چیست؟")
        types = [fact["type"] for fact in result["facts"]]
        self.assertEqual(types, ["course_ambiguous"])
        self.assertEqual(len(result["facts"][0]["matches"]), 2)
        self.assertNotIn("prerequisites", types)

    def test_similar_names_do_not_trigger_clarification_when_signals_differ(self):
        """Duplicates exist for these titles, but context separates them —
        no clarification may be requested for the two example questions."""
        for question in (
            "پیش‌نیاز درس نظریه‌زبان‌ها و ماشین‌ها چیست؟",
            "پیش نیاز درس سیستم عامل چیست؟",
        ):
            with self.subTest(question=question):
                result = self.service.answer(question)
                self.assertNotIn(
                    "course_ambiguous", [fact["type"] for fact in result["facts"]]
                )
                self.assertTrue(result["facts"])

    def test_student_context_resolves_cross_department_tie(self):
        """Same title in two majors; the asking student's field of study
        picks the right row."""
        _course(self.department_cs, "2010", "پروژه", "اصلی")
        _course(self.department_ee, "3010", "پروژه", "اصلی")

        without_user = resolve_course("پیش نیاز درس پروژه چیست؟")
        self.assertTrue(without_user.ambiguous)
        self.assertEqual(
            {c.code for c in without_user.matches}, {"2010", "3010"}
        )

        user = get_user_model().objects.create_user(
            email="context@example.edu", password="Str0ng-Passw0rd!"
        )
        from apps.students.models import StudentProfile

        StudentProfile.objects.create(
            user=user, student_number="40411234", department=self.department_cs
        )
        with_user = resolve_course("پیش نیاز درس پروژه چیست؟", user=user)
        self.assertFalse(with_user.ambiguous)
        self.assertEqual(with_user.course.code, "2010")
