"""Seed command contract (V-13): imports the real dataset, idempotent, guarded."""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.courses.models import ClassSchedule, Course, CourseOffering, CoursePrerequisite
from apps.exams.models import Exam

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
