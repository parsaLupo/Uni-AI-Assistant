"""Professor catalog: search normalization, filters, permission matrix."""

from __future__ import annotations

import pytest

from apps.professors.models import Professor

pytestmark = pytest.mark.django_db


@pytest.fixture
def prof(academic_graph):
    return Professor.objects.create(
        department=academic_graph["department"],
        first_name="کامران",
        last_name="محمدی",
        academic_title="دانشیار",
        is_active=True,
    )


def test_search_matches_arabic_variant_names(authed_client, student, prof):
    client = authed_client(student)
    # Latin digits/kaf variants typed by a user must still find the professor.
    response = client.get("/api/v1/professors/", {"search": "محمدى"})
    assert [p["id"] for p in response.json()["results"]] == [prof.pk]


def test_filter_by_department_and_inactive_excluded(
    authed_client, student, prof, academic_graph
):
    other = Professor.objects.create(
        department=academic_graph["department"], first_name="پنهان", last_name="شده",
        is_active=False,
    )
    client = authed_client(student)
    results = client.get("/api/v1/professors/").json()["results"]
    assert prof.pk in [p["id"] for p in results]
    assert other.pk not in [p["id"] for p in results]

    by_dept = client.get(
        "/api/v1/professors/", {"department": str(academic_graph["department"].pk)}
    ).json()["results"]
    assert [p["id"] for p in by_dept] == [prof.pk]


def test_admin_can_manage_professors(authed_client, admin, academic_graph):
    client = authed_client(admin)
    created = client.post(
        "/api/v1/admin/professors/",
        {
            "first_name": "نگار",
            "last_name": "اکبری",
            "department_id": academic_graph["department"].pk,
            "academic_title": "استادیار",
        },
        format="json",
    )
    assert created.status_code == 201
    prof_id = created.json()["id"]
    assert client.patch(
        f"/api/v1/admin/professors/{prof_id}/", {"office": "دبیرخانه ۳"}, format="json"
    ).status_code == 200
    assert client.delete(f"/api/v1/admin/professors/{prof_id}/").status_code == 204


def test_student_cannot_write_professors(authed_client, student, academic_graph):
    response = authed_client(student).post(
        "/api/v1/admin/professors/",
        {"first_name": "x", "last_name": "y",
         "department_id": academic_graph["department"].pk},
        format="json",
    )
    assert response.status_code == 403
def test_student_sees_professors_from_own_and_cross_department_teachers(
    authed_client, student_profile, academic_graph
):
    from apps.academics.models import Department
    from apps.courses.models import CourseOffering
    from apps.professors.models import Professor

    other_dept = Department.objects.create(
        faculty=academic_graph["faculty"], name="گروه ریاضی", code="99"
    )
    own_prof = Professor.objects.create(
        department=academic_graph["department"], first_name="علی", last_name="رضایی", is_active=True
    )
    cross_prof = Professor.objects.create(
        department=other_dept, first_name="مریم", last_name="احمدی", is_active=True
    )
    unrelated_prof = Professor.objects.create(
        department=other_dept, first_name="پنهان", last_name="شده", is_active=True
    )
    CourseOffering.objects.create(
        course=academic_graph["course"], term=academic_graph["term"], professor=cross_prof, section_code="02"
    )

    client = authed_client(student_profile.user)
    ids = [p["id"] for p in client.get("/api/v1/professors/").json()["results"]]
    assert own_prof.pk in ids
    assert cross_prof.pk in ids
    assert unrelated_prof.pk not in ids

