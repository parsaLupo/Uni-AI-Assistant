"""Course catalog: courses, prerequisite edges, offerings, weekly schedules.

Term-aware by construction — an offering belongs to exactly one term and
history is never rewritten (docs/03 section 5). Constraints from
docs/03 section 6 live in Meta.constraints and are proven by tests that
attempt violations.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.academics.models import AcademicTerm, Department
from apps.common.persian import normalize_persian
from apps.professors.models import Professor


class Course(models.Model):
    """A catalogue course (درس), owned by a department."""

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")
    code = models.CharField(max_length=16, unique=True)
    title = models.CharField(max_length=200)
    credits = models.PositiveSmallIntegerField()
    # Free text: the real dataset carries Persian values (پایه، اصطلاحی…)
    course_type = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)
    normalized_title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            # docs/03 section 4: students look courses up by code constantly.
            models.Index(fields=["code"], name="course_code_idx"),
        ]
        constraints = [
            # docs/03 section 6: unique per (department, code); the global
            # unique on `code` is stricter and satisfies it a fortiori.
            models.UniqueConstraint(
                fields=["department", "code"], name="uniq_course_code_per_department"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.title}"

    def save(self, *args, **kwargs):
        self.normalized_title = normalize_persian(self.title)
        super().save(*args, **kwargs)


class CoursePrerequisite(models.Model):
    """Directed edge: `course` requires `prerequisite_course`."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="prerequisite_edges")
    prerequisite_course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="dependent_edges"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course__code", "prerequisite_course__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "prerequisite_course"], name="uniq_prerequisite_edge"
            ),
            # docs/03 section 6: a course cannot require itself.
            models.CheckConstraint(
                check=~Q(course=F("prerequisite_course")), name="no_self_prerequisite"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} <- {self.prerequisite_course.code}"

    def clean(self):
        if (
            self.course_id
            and self.prerequisite_course_id
            and self.course_id == self.prerequisite_course_id
        ):
            raise ValidationError(
                {"prerequisite_course": "یک درس نمی‌تواند پیش‌نیاز خودش باشد."}
            )


class OfferingStatus(models.TextChoices):
    OPEN = "OPEN", "باز"
    CLOSED = "CLOSED", "بسته"
    CANCELLED = "CANCELLED", "لغوشده"


class CourseOffering(models.Model):
    """One section of a course in one term, taught by one professor."""

    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="offerings")
    term = models.ForeignKey(AcademicTerm, on_delete=models.PROTECT, related_name="offerings")
    professor = models.ForeignKey(
        Professor, on_delete=models.SET_NULL, null=True, blank=True, related_name="offerings"
    )
    section_code = models.CharField(max_length=8)
    capacity = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=12, choices=OfferingStatus.choices, default=OfferingStatus.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-term__starts_at", "course__code", "section_code"]
        indexes = [
            # docs/03 section 4: "offerings of term X" is the catalog query.
            models.Index(fields=["term", "course"], name="offering_term_course_idx"),
            # docs/03 section 4: "what does professor Y teach in term X".
            models.Index(fields=["term", "professor"], name="offering_term_prof_idx"),
        ]
        constraints = [
            # docs/03 section 6: offering identity for enrollment and schedules.
            models.UniqueConstraint(
                fields=["course", "term", "section_code"], name="uniq_section_per_course_term"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} بخش {self.section_code} ({self.term})"

    @property
    def is_historical(self) -> bool:
        return self.term.is_past



class Weekday(models.IntegerChoices):
    """Week starts Saturday (شنبه) in the Iranian calendar."""

    SATURDAY = 5, "شنبه"
    SUNDAY = 0, "یکشنبه"
    MONDAY = 1, "دوشنبه"
    TUESDAY = 2, "سه‌شنبه"
    WEDNESDAY = 3, "چهارشنبه"
    THURSDAY = 4, "پنجشنبه"
    FRIDAY = 6, "جمعه"


class ClassSchedule(models.Model):
    """One weekly meeting row of an offering (admin-owned; ERD COURSE_OFFERING → CLASS_SCHEDULE).

    The student-facing weekly *planner* renders from these rows: a student
    adds offerings to their planner (Enrollment status PLANNED) and the
    timetable is derived from the schedules of the chosen offerings.
    """

    course_offering = models.ForeignKey(
        CourseOffering, on_delete=models.CASCADE, related_name="schedules"
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.CheckConstraint(
                check=Q(start_time__lt=F("end_time")), name="schedule_start_before_end"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_weekday_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}"
