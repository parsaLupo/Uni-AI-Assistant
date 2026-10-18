"""Academic-structure API: permissions, contract shape, term immutability."""

from __future__ import annotations

import pytest

from apps.academics.models import Faculty

pytestmark = pytest.mark.django_db


def test_anonymous_cannot_read_terms(api_client):
    assert api_client.get("/api/v1/terms/").status_code == 401


def test_student_can_read_terms_but_not_write(authed_client, student, academic_graph):
    client = authed_client(student)
    assert client.get("/api/v1/terms/").status_code == 200
    response = client.post(
        "/api/v1/admin/terms/",
        {"name": "x", "academic_year": "1406-1407", "semester_type": "FIRST",
         "starts_at": "2027-03-21", "ends_at": "2028-01-09"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_crud_and_conflict_envelope(authed_client, admin, academic_graph):
    client = authed_client(admin)
    response = client.post(
        "/api/v1/admin/faculties/",
        {"name": "دانشکده ریاضی", "code": "F-MATH"},
        format="json",
    )
    assert response.status_code == 201
    faculty_id = response.json()["id"]

    # Duplicate code -> documented 409 CONFLICT (uniqueness).
    duplicate = client.post(
        "/api/v1/admin/faculties/", {"name": "تکراری", "code": "F-MATH"}, format="json"
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"

    deleted = client.delete(f"/api/v1/admin/faculties/{faculty_id}/")
    assert deleted.status_code == 204


def test_pagination_contract_shape(authed_client, student, academic_graph):
    client = authed_client(student)
    for i in range(3):
        Faculty.objects.create(name=f"دانشکده {i}", code=f"F-{i}")
    response = client.get("/api/v1/terms/?page=1&page_size=2")
    body = response.json()
    assert set(body) == {"count", "next", "previous", "results"}
    assert body["count"] >= 1
    assert isinstance(body["results"], list)


def test_past_term_is_immutable(authed_client, admin, academic_graph):
    client = authed_client(admin)
    past = academic_graph["past_term"]
    response = client.patch(
        f"/api/v1/admin/terms/{past.pk}/", {"name": "ویرایش غیرمجاز"}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    past.refresh_from_db()
    assert past.name != "ویرایش غیرمجاز"


def test_second_current_term_rejected_with_409(authed_client, admin, academic_graph):
    client = authed_client(admin)
    new_term = client.post(
        "/api/v1/admin/terms/",
        {"name": "ترم دوم جاری", "academic_year": "1406-1407", "semester_type": "SECOND",
         "starts_at": "2027-10-01", "ends_at": "2028-03-20", "is_current": True},
        format="json",
    )
    assert new_term.status_code == 409
    assert new_term.json()["error"]["code"] == "CONFLICT"


def test_department_delete_blocked_when_it_has_courses(authed_client, admin, academic_graph):
    client = authed_client(admin)
    response = client.delete(
        f"/api/v1/admin/departments/{academic_graph['department'].pk}/"
    )
    assert response.status_code == 409
