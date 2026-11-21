"""Test bootstrap.

Fixes a deterministic environment before Django settings are imported:

* PostgreSQL + pgvector is the only supported database engine (ADR-002), so the
  suite needs a real PostgreSQL server. Point ``TEST_DATABASE_URL`` at a
  disposable database; ``scripts/test-backend.ps1`` starts one automatically.
  There is deliberately no SQLite fallback: a green suite must exercise the
  engine the release stack actually runs.
* The Django test runner creates and drops ``test_<name>`` inside that server,
  so the configured database itself is never written to.
* ``DJANGO_SECRET_KEY`` is a throwaway value; no secret is ever committed.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# pytest-django imports Django settings (and therefore config.environment)
# before this file runs. config.environment promotes TEST_DATABASE_URL to
# DATABASE_URL at that point, so the promoted value is what we check here.
if not os.environ.get("DATABASE_URL"):
    raise RuntimeError(
        "Backend tests require PostgreSQL + pgvector (SQLite is not supported).\n"
        "Start a disposable database and set TEST_DATABASE_URL, for example:\n"
        "  docker run --rm -d --name usa-test-db -p 55432:5432 "
        "-e POSTGRES_DB=usa_test -e POSTGRES_USER=usa_test "
        "-e POSTGRES_PASSWORD=test_password pgvector/pgvector:0.8.6-pg16\n"
        "  $env:TEST_DATABASE_URL='postgresql://usa_test:test_password@localhost:55432/usa_test'\n"
        "  python -m pytest\n"
        "Or simply run: scripts/test-backend.ps1"
    )

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key-not-a-real-secret")
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost")
os.environ.setdefault("DJANGO_DEBUG", "false")

# --- Shared fixtures (Phase 04+) -------------------------------------------
# Kept at the root so every app's suite can use them; no DB access happens at
# import time (fixtures are lazy).

import pytest  # noqa: E402
from django.core.cache import cache  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

TEST_PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """DRF throttles share the default cache across tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


def make_user(email: str, role: str = "STUDENT", **extra):
    from apps.accounts.models import User

    return User.objects.create_user(
        email=email, password=TEST_PASSWORD, role=role, **extra
    )


@pytest.fixture
def student():
    return make_user("student@example.edu", "STUDENT", first_name="سارا", last_name="محمدی")


@pytest.fixture
def professor_user():
    return make_user("professor@example.edu", "PROFESSOR")


@pytest.fixture
def admin():
    return make_user("admin@example.edu", "ADMIN")


@pytest.fixture
def superadmin():
    return make_user("root@example.edu", "SUPERADMIN")


@pytest.fixture
def authed_client():
    """Factory: APIClient authenticated as the given user (no login/throttle)."""

    def _as(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _as


@pytest.fixture
def academic_graph():
    """A small academic graph: faculty → department → course, current term."""
    from datetime import date

    from apps.academics.models import AcademicTerm, Department, Faculty
    from apps.courses.models import Course

    faculty = Faculty.objects.create(name="دانشکده مهندسی کامپیوتر", code="F-CE")
    department = Department.objects.create(faculty=faculty, name="گروه مهندسی کامپیوتر", code="16")
    course = Course.objects.create(
        department=department, code="1916001", title="کارگاه کامپیوتر", credits=1
    )
    prereq = Course.objects.create(
        department=department, code="1916002", title="مبانی برنامه‌سازی", credits=3
    )
    term = AcademicTerm.objects.create(
        name="نیمسال اول ۱۴۰۵-۱۴۰۶",
        academic_year="1405-1406",
        semester_type="FIRST",
        starts_at=date(2026, 3, 21),
        ends_at=date(2027, 1, 9),
        is_current=True,
    )
    past_term = AcademicTerm.objects.create(
        name="نیمسال اول ۱۴۰۴-۱۴۰۵",
        academic_year="1404-1405",
        semester_type="FIRST",
        starts_at=date(2025, 3, 21),
        ends_at=date(2026, 1, 9),
        is_current=False,
    )
    return {
        "faculty": faculty,
        "department": department,
        "course": course,
        "prereq": prereq,
        "term": term,
        "past_term": past_term,
    }


@pytest.fixture
def student_profile(student, academic_graph):
    from apps.students.models import StudentProfile

    return StudentProfile.objects.create(
        user=student,
        student_number="40411234",
        department=academic_graph["department"],
        faculty=academic_graph["faculty"],
    )

