"""Phase 13 — admin analytics dashboard + audit-log viewer.

Privacy rule (checklist): metrics are computed from real application data and
the query layer never exposes raw message content; the dashboard payload is
aggregate-only. The dashboard and viewer are admin-only (students rejected).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.analytics.models import AIRequestEvent, AuditLog
from apps.analytics.services import record_ai_request
from apps.conversations.models import Conversation, Message, MessageSource
from apps.documents.models import Document, DocumentChunk

pytestmark = pytest.mark.django_db

DASHBOARD = "/api/v1/admin/analytics/dashboard/"
AUDIT_LOG = "/api/v1/admin/analytics/audit-log/"


def make_user(email: str, role: str = "STUDENT", **extra):
    User = get_user_model()
    return User.objects.create_user(
        email=email, password="Str0ng-Passw0rd!", role=role, **extra
    )


def _message(
    conversation, role: str, *, content: str = "", **extra
) -> Message:
    return Message.objects.create(conversation=conversation, role=role, content=content, **extra)


def _grounded_universe(student) -> dict:
    """2 users, 2 questions, answer modes, one cited document (real rows)."""
    other = make_user("other@example.edu")
    conversation = Conversation.objects.create(user=student)
    _message(conversation, Message.Role.USER, content="سوال اول؟")
    _message(conversation, Message.Role.USER, content="سوال دوم؟")
    _message(
        conversation,
        Message.Role.ASSISTANT,
        retrieval_mode="HYBRID",
        latency_ms=1200,
    )
    _message(
        conversation,
        Message.Role.ASSISTANT,
        retrieval_mode="STRUCTURED",
        latency_ms=300,
        insufficient_evidence=True,
    )

    cited = Document.objects.create(title="آیین‌نامه آموزشی", document_type="REG")
    uncited = Document.objects.create(title="سندی بدون ارجاع")
    chunk = DocumentChunk.objects.create(
        document=cited, chunk_index=0, content="متن سند"
    )
    assistant_row = Message.objects.filter(role=Message.Role.ASSISTANT).first()
    MessageSource.objects.create(message=assistant_row, document_chunk=chunk)
    MessageSource.objects.create(message=assistant_row, document_chunk=chunk)
    return {"other": other, "cited": cited, "uncited": uncited}


# --- Access control (AC: dashboard is admin-only and rejects students) --------


def test_dashboard_rejects_students_and_anonymous(authed_client, api_client, student):
    assert authed_client(student).get(DASHBOARD).status_code == 403
    assert api_client.get(DASHBOARD).status_code == 401
    assert authed_client(student).get(AUDIT_LOG).status_code == 403
    assert api_client.get(AUDIT_LOG).status_code == 401


def test_audit_log_viewer_is_write_protected(authed_client, admin):
    client = authed_client(admin)
    for method in ("post", "patch", "put", "delete"):
        response = getattr(client, method)(AUDIT_LOG, {}, format="json")
        assert response.status_code == 405, method


# --- Dashboard metrics come from real data ------------------------------------


def test_dashboard_aggregates_real_data(authed_client, admin, student):
    make_user("idle@example.edu")  # inactive user must not count
    User = get_user_model()
    User.objects.filter(email="idle@example.edu").update(is_active=False)
    student.last_login = timezone.now()
    student.save(update_fields=["last_login"])

    _grounded_universe(student)
    record_ai_request(user=student, mode="HYBRID", outcome="OK", latency_ms=900)
    record_ai_request(user=student, outcome="AI_PROVIDER_ERROR", latency_ms=50)

    payload = authed_client(admin).get(DASHBOARD).json()

    users = payload["users"]
    # admin + student + the grounded-universe second user
    assert users["active_users"] == 3
    assert users["recently_active_users"] == 1  # student logged in "just now"
    assert {row["role"]: row["count"] for row in users["by_role"]} == {
        "ADMIN": 1,
        "STUDENT": 2,
    }

    questions = payload["questions"]
    assert questions["total"] == 2
    assert questions["answers"] == 2
    assert questions["insufficient_evidence"] == 1

    assert {row["mode"]: row["count"] for row in payload["topic_distribution"]} == {
        "HYBRID": 1,
        "STRUCTURED": 1,
    }

    top = payload["top_documents"]
    assert len(top) == 1  # the uncited document is not "most used"
    assert top[0]["title"] == "آیین‌نامه آموزشی"
    assert top[0]["citation_count"] == 2

    ai = payload["ai"]
    assert ai["total_requests"] == 2
    assert ai["error_count"] == 1
    assert ai["avg_latency_ms"] == 900.0
    assert payload["documents_total"] == 2

    # The payload is aggregate-only: no raw message content ever leaves.
    serialised = repr(payload)
    assert "سوال" not in serialised
    assert "متن سند" not in serialised


def test_dashboard_empty_database_is_honest(authed_client, admin, academic_graph):
    payload = authed_client(admin).get(DASHBOARD).json()
    assert payload["users"]["active_users"] == 1
    assert payload["questions"]["total"] == 0
    assert payload["topic_distribution"] == []
    assert payload["top_documents"] == []
    assert payload["ai"] == {
        "total_requests": 0,
        "error_count": 0,
        "avg_latency_ms": None,
    }


# --- Audit-log viewer ---------------------------------------------------------


def test_audit_log_viewer_lists_and_filters(authed_client, admin, academic_graph):
    client = authed_client(admin)
    client.post(
        "/api/v1/admin/faculties/", {"name": "دانشکده ریاضی", "code": "F-MATH"},
        format="json",
    )
    client.post(
        "/api/v1/admin/terms/",
        {
            "name": "ترم آزمایشی",
            "academic_year": "1406-1407",
            "semester_type": "FIRST",
            "starts_at": "2027-03-21",
            "ends_at": "2028-01-09",
        },
        format="json",
    )

    rows = client.get(AUDIT_LOG).json()["results"]
    assert len(rows) == 2
    assert all("metadata" in row for row in rows)

    faculties_only = client.get(f"{AUDIT_LOG}?entity_type=Faculty").json()["results"]
    assert {row["entity_type"] for row in faculties_only} == {"academics.Faculty"}

    terms_only = client.get(
        f"{AUDIT_LOG}?action=CREATE&entity_type=academics.AcademicTerm"
    ).json()["results"]
    assert len(terms_only) == 1
    assert terms_only[0]["entity_type"] == "academics.AcademicTerm"


# --- AI telemetry recording ----------------------------------------------------


def test_ask_view_records_ok_event(authed_client, student, academic_graph):
    response = authed_client(student).post(
        "/api/v1/ai/ask/", {"question": "شرایط مشروطی چیست؟"}, format="json"
    )
    assert response.status_code == 200

    rows = AIRequestEvent.objects.all()
    assert rows.count() == 1
    row = rows.first()
    assert row.outcome == "OK"
    assert row.mode == response.json()["mode"]
    assert row.latency_ms is not None
    assert row.user_id == student.pk


def test_validation_failure_is_not_telemetrised(authed_client, student):
    authed_client(student).post("/api/v1/ai/ask/", {"question": "  "}, format="json")
    assert AIRequestEvent.objects.count() == 0


def test_record_never_raises(authed_client, student, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(AIRequestEvent.objects, "create", explode)
    record_ai_request(user=student, mode="RAG", outcome="OK", latency_ms=1)
    assert AIRequestEvent.objects.count() == 0
