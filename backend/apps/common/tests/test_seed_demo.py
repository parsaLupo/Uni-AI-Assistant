"""Phase 16 demo-seed contract.

`seed_demo` is the only command allowed to create demo identities in a
release/local-demo stack; it must be explicitly enabled, use the local
DEMO_PASSWORD, create all four roles, and be idempotent.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import Role, User
from apps.notifications.models import Notification
from apps.students.models import Enrollment, EnrollmentStatus

pytestmark = pytest.mark.django_db

DATA_DIR = Path(settings.BASE_DIR).parent / "data"
DEMO_PASSWORD = "Demo-Test-Passw0rd-16"


def test_seed_demo_requires_demo_mode(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    with pytest.raises(CommandError, match="DEMO_MODE=true"):
        call_command("seed_demo", data_dir=str(DATA_DIR))


def test_seed_demo_refuses_a_weak_password(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_PASSWORD", "short")
    with pytest.raises(CommandError, match="DEMO_PASSWORD"):
        call_command("seed_demo", data_dir=str(DATA_DIR))


def test_seed_demo_refuses_the_old_public_password(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    # Split so the removed public literal never appears verbatim in the tree.
    monkeypatch.setenv("DEMO_PASSWORD", "Demo-" + "Passw0rd!")
    with pytest.raises(CommandError, match="DEMO_PASSWORD"):
        call_command("seed_demo", data_dir=str(DATA_DIR))


def test_seed_demo_creates_all_roles_history_and_is_idempotent(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_PASSWORD", DEMO_PASSWORD)

    call_command("seed_demo", data_dir=str(DATA_DIR))

    expected = {
        "root@semnan.local": Role.SUPERADMIN,
        "admin@semnan.local": Role.ADMIN,
        "student@semnan.local": Role.STUDENT,
        "professor@semnan.local": Role.PROFESSOR,
    }
    for email, role in expected.items():
        user = User.objects.get(email=email)
        assert user.role == role
        assert user.check_password(DEMO_PASSWORD)

    student = User.objects.get(email="student@semnan.local")
    profile = student.student_profile
    assert profile.student_number == "40411234"
    assert profile.onboarding_complete is True
    assert Enrollment.objects.filter(student=profile, status=EnrollmentStatus.PLANNED).count() >= 1
    assert Enrollment.objects.filter(student=profile, status=EnrollmentStatus.PASSED).count() >= 1
    assert Notification.objects.filter(user=student).exists()

    users = User.objects.count()
    enrollments = Enrollment.objects.count()
    notifications = Notification.objects.count()

    call_command("seed_demo", data_dir=str(DATA_DIR))

    assert User.objects.count() == users
    assert Enrollment.objects.count() == enrollments
    assert Notification.objects.count() == notifications
