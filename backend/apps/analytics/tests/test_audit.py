"""Audit log contract (docs/api/admin.md: every admin write is audited)."""

from __future__ import annotations

import pytest

from apps.analytics.models import AuditAction, AuditLog

pytestmark = pytest.mark.django_db


def test_create_update_delete_each_emit_an_audit_row(authed_client, admin, academic_graph):
    client = authed_client(admin)
    created = client.post(
        "/api/v1/admin/faculties/", {"name": "دانشکده فیزیک", "code": "F-PHY"},
        format="json",
    )
    assert created.status_code == 201
    faculty_id = created.json()["id"]

    client.patch(
        f"/api/v1/admin/faculties/{faculty_id}/", {"description": "توضیح"},
        format="json",
    )
    client.delete(f"/api/v1/admin/faculties/{faculty_id}/")

    rows = AuditLog.objects.filter(entity_type="academics.Faculty", entity_id=str(faculty_id))
    # Meta ordering is newest-first; assert the set of actions, not row order.
    assert set(rows.values_list("action", flat=True)) == {
        AuditAction.CREATE,
        AuditAction.UPDATE,
        AuditAction.DELETE,
    }
    assert rows.count() == 3
    assert all(row.actor == admin for row in rows)


def test_public_reads_are_not_audited(authed_client, student, academic_graph):
    authed_client(student).get("/api/v1/terms/")
    assert not AuditLog.objects.exists()


def test_anonymous_cannot_write_anything_admin(api_client, academic_graph):
    for path in ("/api/v1/admin/faculties/", "/api/v1/admin/terms/",
                 "/api/v1/admin/enrollments/", "/api/v1/admin/announcements/"):
        assert api_client.get(path).status_code == 401, path
