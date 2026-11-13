"""Phase 14 — table-driven permission matrix over every documented endpoint.

The matrix mirrors `openapi.yaml` one-to-one: every path is listed with the
methods it supports and the expected status (or the ``ALLOWED`` sentinel) for
four callers — anonymous, STUDENT, PROFESSOR, ADMIN.

Assertions encode *permission boundaries*, not full CRUD validation:

* ``401`` — the caller must not even reach business logic (IsAuthenticated).
* ``403`` — the caller reaches the view but is rejected by the role gate
  (IsAdmin) before any object lookup.
* ``ALLOWED`` — the caller may proceed; any non-401/403 outcome is acceptable
  (200/204/400/404/405/409 — payload validity is covered by the per-app suites).
* Owner-scoped detail routes (conversations, planner) deliberately return
  ``404`` for other users' ids — the Phase 10 anti-enumeration decision — so
  the matrix asserts 404, proving a foreign id leaks no information.

A change that widens or narrows access without updating this table breaks the
suite; the table is the review artifact.
"""

import re

import pytest

ALLOWED = -1  # sentinel: any status except 401/403
DENIED_ROLES = {"anonymous": 401, "student": 403, "professor": 403, "admin": ALLOWED}
PUBLIC_ALLOWED = dict.fromkeys(DENIED_ROLES, ALLOWED)
AUTH_REQUIRED = dict.fromkeys(DENIED_ROLES, 401)
AUTH_ALLOWED = {"anonymous": 401, "student": ALLOWED, "professor": ALLOWED, "admin": ALLOWED}
# Academic reads are authenticated (global DRF default; docs promise no
# anonymous access anywhere) — students/professors/admins all read.
READS_AUTH = {"anonymous": 401, "student": 200, "professor": 200, "admin": 200}
READS_ALLOWED = {"anonymous": 401, "student": ALLOWED, "professor": ALLOWED, "admin": ALLOWED}
# Double-submit CSRF (ADR-014): without a cookie+header pair these 403 before
# doing anything, regardless of authentication state.
CSRF_GATE = dict.fromkeys(DENIED_ROLES, 403)
# Liveness is genuinely anonymous.
PUBLIC_HEALTH = dict.fromkeys(DENIED_ROLES, 200)
# Student self-service: `_get_profile` raises PermissionDenied for other roles.
STUDENT_ONLY = {"anonymous": 401, "student": ALLOWED, "professor": 403, "admin": 403}
# Owner-scoped resources hide foreign ids (Phase 10 anti-enumeration).
OWNER_SCOPED = {"anonymous": 401, "student": 404, "professor": 404, "admin": 404}

FAKE_ID = 999999

# (path template, method, {role: expected status})
PERMISSION_MATRIX: list[tuple[str, str, dict[str, int]]] = [
    # --- health + contract ---------------------------------------------------
    ("/api/v1/health/", "GET", PUBLIC_HEALTH),
    # --- auth (AllowAny; refresh/logout additionally CSRF-gated) -------------
    ("/api/v1/auth/register/", "POST", PUBLIC_ALLOWED),
    ("/api/v1/auth/login/", "POST", PUBLIC_ALLOWED),
    # No cookie+CSRF pair → the double-submit gate fires before anything else.
    ("/api/v1/auth/refresh/", "POST", CSRF_GATE),
    ("/api/v1/auth/logout/", "POST", CSRF_GATE),
    ("/api/v1/auth/me/", "GET", AUTH_ALLOWED),
    # --- public academic reads (authentication required; no anonymous tier) --
    ("/api/v1/terms/", "GET", READS_AUTH),
    (f"/api/v1/terms/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/departments/", "GET", READS_AUTH),
    (f"/api/v1/departments/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/courses/", "GET", READS_AUTH),
    (f"/api/v1/courses/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/course-offerings/", "GET", READS_AUTH),
    (f"/api/v1/course-offerings/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/professors/", "GET", READS_AUTH),
    (f"/api/v1/professors/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/exams/", "GET", READS_AUTH),
    (f"/api/v1/exams/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/calendar/events/", "GET", READS_AUTH),
    (f"/api/v1/calendar/events/{FAKE_ID}/", "GET", READS_ALLOWED),
    ("/api/v1/announcements/", "GET", READS_AUTH),
    (f"/api/v1/announcements/{FAKE_ID}/", "GET", READS_ALLOWED),
    # --- student self-service (server rejects non-students with 403) ---------
    ("/api/v1/students/me/", "GET", STUDENT_ONLY),
    ("/api/v1/students/me/", "PATCH", STUDENT_ONLY),
    ("/api/v1/students/planner/", "GET", STUDENT_ONLY),
    ("/api/v1/students/planner/", "POST", STUDENT_ONLY),
    (f"/api/v1/students/planner/{FAKE_ID}/", "PATCH", STUDENT_ONLY),
    (f"/api/v1/students/planner/{FAKE_ID}/", "DELETE", STUDENT_ONLY),
    ("/api/v1/students/me/course-selection/", "POST", STUDENT_ONLY),
    # --- AI (any authenticated role may ask; students are the primary users) --
    ("/api/v1/ai/ask/", "POST", AUTH_ALLOWED),
    ("/api/v1/ai/ask/stream/", "POST", AUTH_ALLOWED),
    # --- notifications (user-scoped, any role has its own inbox) -------------
    ("/api/v1/notifications/", "GET", AUTH_ALLOWED),
    ("/api/v1/notifications/unread-count/", "GET", AUTH_ALLOWED),
    ("/api/v1/notifications/mark-all-read/", "POST", AUTH_ALLOWED),
    (f"/api/v1/notifications/{FAKE_ID}/mark-read/", "POST", AUTH_ALLOWED),
    # --- conversations (owner-scoped: foreign/nonexistent id → 404) ----------
    ("/api/v1/conversations/", "GET", AUTH_ALLOWED),
    ("/api/v1/conversations/", "POST", AUTH_ALLOWED),
    (f"/api/v1/conversations/{FAKE_ID}/", "GET", OWNER_SCOPED),
    (f"/api/v1/conversations/{FAKE_ID}/", "PATCH", OWNER_SCOPED),
    (f"/api/v1/conversations/{FAKE_ID}/", "DELETE", OWNER_SCOPED),
    (f"/api/v1/conversations/{FAKE_ID}/messages/", "POST", OWNER_SCOPED),
    # --- admin: accounts ------------------------------------------------------
    ("/api/v1/admin/users/", "GET", DENIED_ROLES),
    ("/api/v1/admin/users/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/users/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/users/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/users/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    # --- admin: academics -----------------------------------------------------
    ("/api/v1/admin/faculties/", "GET", DENIED_ROLES),
    ("/api/v1/admin/faculties/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/faculties/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/faculties/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/faculties/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    ("/api/v1/admin/departments/", "GET", DENIED_ROLES),
    ("/api/v1/admin/departments/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/departments/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/departments/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/departments/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    ("/api/v1/admin/terms/", "GET", DENIED_ROLES),
    ("/api/v1/admin/terms/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/terms/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/terms/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    # no DELETE on terms by contract (D4) — 405, still not 401/403
    (f"/api/v1/admin/terms/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    # --- admin: courses / offerings / schedules / exams -----------------------
    ("/api/v1/admin/courses/", "GET", DENIED_ROLES),
    ("/api/v1/admin/courses/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/courses/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/courses/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/courses/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    (f"/api/v1/admin/courses/{FAKE_ID}/prerequisites/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/courses/{FAKE_ID}/prerequisites/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/prerequisites/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    ("/api/v1/admin/offerings/", "GET", DENIED_ROLES),
    ("/api/v1/admin/offerings/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/schedules/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/schedules/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/schedules/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/schedules/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/exam/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/exam/", "PUT", DENIED_ROLES),
    (f"/api/v1/admin/offerings/{FAKE_ID}/exam/", "PATCH", DENIED_ROLES),
    # --- admin: professors / students / enrollments ---------------------------
    ("/api/v1/admin/professors/", "GET", DENIED_ROLES),
    ("/api/v1/admin/professors/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/professors/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/professors/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/professors/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    ("/api/v1/admin/students/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/students/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/students/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    ("/api/v1/admin/enrollments/", "GET", DENIED_ROLES),
    ("/api/v1/admin/enrollments/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/enrollments/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/enrollments/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/enrollments/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    # --- admin: calendar / announcements --------------------------------------
    ("/api/v1/admin/calendar/events/", "GET", DENIED_ROLES),
    ("/api/v1/admin/calendar/events/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/calendar/events/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/calendar/events/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    ("/api/v1/admin/announcements/", "GET", DENIED_ROLES),
    ("/api/v1/admin/announcements/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/announcements/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/announcements/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/announcements/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    # --- admin: documents -------------------------------------------------------
    ("/api/v1/admin/documents/", "GET", DENIED_ROLES),
    ("/api/v1/admin/documents/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/documents/{FAKE_ID}/", "GET", DENIED_ROLES),
    (f"/api/v1/admin/documents/{FAKE_ID}/", "PATCH", DENIED_ROLES),
    (f"/api/v1/admin/documents/{FAKE_ID}/", "DELETE", DENIED_ROLES),
    (f"/api/v1/admin/documents/{FAKE_ID}/activate/", "POST", DENIED_ROLES),
    (f"/api/v1/admin/documents/{FAKE_ID}/retry/", "POST", DENIED_ROLES),
    # --- admin: analytics -------------------------------------------------------
    ("/api/v1/admin/analytics/dashboard/", "GET", DENIED_ROLES),
    ("/api/v1/admin/analytics/audit-log/", "GET", DENIED_ROLES),
]


def _matrix_ids():
    return [f"{path} {method}" for path, method, _ in PERMISSION_MATRIX]


@pytest.mark.django_db
@pytest.mark.parametrize("path,method,expected", PERMISSION_MATRIX, ids=_matrix_ids())
def test_permission_matrix(path, method, expected, authed_client, student, professor_user, admin):
    """Every role's status for every endpoint matches the reviewed table."""
    callers = {
        "anonymous": authed_client(None),
        "student": authed_client(student),
        "professor": authed_client(professor_user),
        "admin": authed_client(admin),
    }
    for role, caller in callers.items():
        response = getattr(caller, method.lower())(path, data={}, format="json")
        status = response.status_code
        if expected[role] == ALLOWED:
            assert status not in (401, 403), (
                f"{method} {path} as {role}: got {status}; permission boundary broken"
            )
        else:
            assert status == expected[role], (
                f"{method} {path} as {role}: expected {expected[role]}, got {status}"
            )


def _normalize(path: str) -> str:
    """Strip trailing slash; unify path params (`{id}` == `999999` == `{course_id}`)."""
    path = re.sub(r"\{[^}]+\}", "{}", path.rstrip("/"))
    return re.sub(r"/\d+(?=/|$)", "/{}", path)


def test_matrix_covers_every_openapi_path():
    """The table is exhaustive against the committed contract (ADR-012)."""
    from pathlib import Path

    yaml_path = Path(__file__).resolve().parents[4] / "openapi.yaml"
    schema_paths = set(
        re.findall(r"^  (/.+?):$", yaml_path.read_text(encoding="utf-8"), re.MULTILINE)
    )
    covered = {_normalize(path) for path, _, _ in PERMISSION_MATRIX}
    missing = {
        path
        for path in schema_paths
        # The schema endpoint is excluded from its own output (ADR-012).
        if _normalize(path) not in covered and path != "/api/v1/schema/"
    }
    assert not missing, f"openapi paths missing from the permission matrix: {sorted(missing)}"
