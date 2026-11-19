"""Bulk student import: template, inspect, validate/preview, confirm, reports.

Covers the full contract in `docs/api/admin.md`: unsafe files are rejected,
nothing is written during preview, confirmation executes exactly the bytes
that were validated, imports are idempotent and additive, existing academic
history is never overwritten, and generated passwords only appear once.
"""

from __future__ import annotations

import datetime as dt
import io
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook, load_workbook

from apps.academics.models import AcademicTerm, Department, Faculty, TermSemester
from apps.accounts.models import Role, User
from apps.analytics.models import AuditLog
from apps.courses.models import Course, CourseOffering, OfferingStatus
from apps.students.models import DegreeLevel, Enrollment, EnrollmentStatus, StudentProfile

from .conftest import TEST_PASSWORD, login, make_user

pytestmark = pytest.mark.django_db

BASE = "/api/v1/admin/students/import"
TEMPLATE_URL = f"{BASE}/template/"
INSPECT_URL = f"{BASE}/inspect/"
VALIDATE_URL = f"{BASE}/validate/"
CONFIRM_URL = f"{BASE}/confirm/"
REPORTS_URL = f"{BASE}/reports/"

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

STUDENT_HEADERS = [
    "student_id",
    "first_name",
    "last_name",
    "email",
    "department",
    "degree",
    "entry_year",
    "current_term",
    "gpa",
]
PASSED_HEADERS = ["student_id", "course_code", "grade", "term"]
ENROLL_HEADERS = ["student_id", "course_code", "group_code", "term"]

CURRENT_TERM = "نیمسال اول 1405-1406"
PAST_TERM = "نیمسال اول 1404-1405"


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def catalog():
    """Two departments, courses, a past/current/future term and offerings."""
    faculty = Faculty.objects.create(name="دانشکده مهندسی", code="ENG")
    computer = Department.objects.create(faculty=faculty, name="مهندسی کامپیوتر", code="COMP")
    math = Department.objects.create(faculty=faculty, name="ریاضی", code="MATH")
    cs1 = Course.objects.create(
        department=computer, code="CS101", title="برنامه‌نویسی", credits=3
    )
    cs2 = Course.objects.create(
        department=computer, code="CS102", title="ساختمان داده", credits=3
    )
    math1 = Course.objects.create(department=math, code="MATH101", title="ریاضی ۱", credits=3)

    past = AcademicTerm.objects.create(
        name=PAST_TERM,
        academic_year="1404-1405",
        semester_type=TermSemester.FIRST,
        starts_at=dt.date(2025, 9, 1),
        ends_at=dt.date(2026, 1, 20),
    )
    current = AcademicTerm.objects.create(
        name=CURRENT_TERM,
        academic_year="1405-1406",
        semester_type=TermSemester.FIRST,
        starts_at=dt.date(2026, 9, 1),
        ends_at=dt.date(2027, 1, 20),
        is_current=True,
    )
    future = AcademicTerm.objects.create(
        name="نیمسال دوم 1405-1406",
        academic_year="1405-1406",
        semester_type=TermSemester.SECOND,
        starts_at=dt.date(2027, 2, 1),
        ends_at=dt.date(2027, 6, 30),
    )
    offerings = {
        "cs1_current": CourseOffering.objects.create(
            course=cs1, term=current, section_code="01", capacity=30
        ),
        "cs2_current": CourseOffering.objects.create(
            course=cs2, term=current, section_code="02", capacity=30
        ),
        "math_current": CourseOffering.objects.create(
            course=math1, term=current, section_code="01", capacity=30
        ),
        "cs1_past": CourseOffering.objects.create(
            course=cs1,
            term=past,
            section_code="01",
            capacity=0,
            status=OfferingStatus.CLOSED,
        ),
    }
    return {
        "faculty": faculty,
        "computer": computer,
        "math": math,
        "cs1": cs1,
        "cs2": cs2,
        "math1": math1,
        "past": past,
        "current": current,
        "future": future,
        "offerings": offerings,
    }


def student_row(
    number: str = "40211234",
    email: str = "sara@example.edu",
    department: str = "COMP",
    degree: str = "کارشناسی",
    entry_year: str = "1402",
    current_term: str = "3",
    gpa: str = "17.66",
    first: str = "سارا",
    last: str = "محمدی",
) -> list:
    return [number, first, last, email, department, degree, entry_year, current_term, gpa]


# ── Workbook helpers ──────────────────────────────────────────────────────


def build_workbook(sheets: dict[str, tuple[list[str], list[list]]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, (headers, rows) in sheets.items():
        sheet = workbook.create_sheet(title)
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def default_sheets(
    students: list[list] | None = None,
    passed: list[list] | None = None,
    enrollments: list[list] | None = None,
    student_headers: list[str] | None = None,
    passed_headers: list[str] | None = None,
    enrollment_headers: list[str] | None = None,
) -> dict[str, tuple[list[str], list[list]]]:
    sheets: dict[str, tuple[list[str], list[list]]] = {}
    sheets["Students"] = (student_headers or STUDENT_HEADERS, students or [student_row()])
    if passed is not None:
        sheets["PassedCourses"] = (passed_headers or PASSED_HEADERS, passed)
    if enrollments is not None:
        sheets["CurrentEnrollments"] = (enrollment_headers or ENROLL_HEADERS, enrollments)
    return sheets


def mapping_json(
    students: list[str] | None = None,
    passed: list[str] | None = None,
    enrollments: list[str] | None = None,
) -> str:
    """Canonical mapping: identity columns, one entry per requested sheet."""
    entries = [
        {
            "role": "students",
            "sheet": "Students",
            "columns": {name: name for name in (students or STUDENT_HEADERS)},
        }
    ]
    if passed:
        entries.append(
            {
                "role": "passed_courses",
                "sheet": "PassedCourses",
                "columns": {name: name for name in passed},
            }
        )
    if enrollments:
        entries.append(
            {
                "role": "current_enrollments",
                "sheet": "CurrentEnrollments",
                "columns": {name: name for name in enrollments},
            }
        )
    return json.dumps({"sheets": entries}, ensure_ascii=False)


def upload(content: bytes, name: str = "roster.xlsx") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=XLSX)


def validate(client, content: bytes, mapping: str, mode: str = "create_only"):
    return client.post(
        VALIDATE_URL,
        {"file": upload(content), "mapping": mapping, "mode": mode},
        format="multipart",
    )


def confirm(
    client,
    content: bytes,
    mapping: str,
    mode: str = "create_only",
    expected_hash: str | None = None,
    confirm_flag: bool = True,
):
    from apps.accounts.student_import import file_hash

    return client.post(
        CONFIRM_URL,
        {
            "file": upload(content),
            "mapping": mapping,
            "mode": mode,
            "expected_hash": expected_hash or file_hash(content),
            "confirm": "true" if confirm_flag else "false",
        },
        format="multipart",
    )


def errors_by_code(report: dict, code: str) -> list[dict]:
    return [issue for issue in report["errors"] if issue["code"] == code]


# ── Template ──────────────────────────────────────────────────────────────


def test_template_has_the_four_documented_sheets(api_client, admin):
    login(api_client, admin.email)

    response = api_client.get(TEMPLATE_URL)

    assert response.status_code == 200
    assert response["Content-Type"] == XLSX
    assert "attachment" in response["Content-Disposition"]
    workbook = load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["راهنما", "Students", "PassedCourses", "CurrentEnrollments"]
    assert [cell.value for cell in workbook["Students"][1]] == STUDENT_HEADERS
    assert [cell.value for cell in workbook["PassedCourses"][1]] == PASSED_HEADERS
    assert [cell.value for cell in workbook["CurrentEnrollments"][1]] == ENROLL_HEADERS


def test_template_requires_admin(api_client, student):
    login(api_client, student.email)
    assert api_client.get(TEMPLATE_URL).status_code == 403


def test_import_endpoints_require_authentication(api_client):
    assert api_client.get(TEMPLATE_URL).status_code == 401
    assert api_client.post(INSPECT_URL, {}, format="multipart").status_code == 401
    assert api_client.get(REPORTS_URL).status_code == 401


# ── Inspect ───────────────────────────────────────────────────────────────


def test_inspect_suggests_roles_and_mapping_for_persian_headers(api_client, admin):
    login(api_client, admin.email)
    persian = [
        "شماره دانشجویی",
        "نام",
        "نام خانوادگی",
        "ایمیل",
        "رشته",
        "مقطع",
        "سال ورود",
        "ترم جاری",
        "معدل",
    ]
    content = build_workbook(
        default_sheets(student_headers=persian, passed=[[student_row()[0], "CS101", 18, PAST_TERM]])
    )

    response = api_client.post(INSPECT_URL, {"file": upload(content)}, format="multipart")

    assert response.status_code == 200
    body = response.json()
    assert len(body["file_hash"]) == 64
    sheets = {sheet["name"]: sheet for sheet in body["sheets"]}
    assert sheets["Students"]["suggested_role"] == "students"
    assert sheets["Students"]["suggested_mapping"]["student_id"] == "شماره دانشجویی"
    assert sheets["Students"]["suggested_mapping"]["gpa"] == "معدل"
    assert sheets["PassedCourses"]["suggested_role"] == "passed_courses"
    # Samples are display strings (never raw formulas/objects).
    assert sheets["Students"]["sample_rows"][0][0] == "40211234"


def test_inspect_never_guesses_an_ambiguous_header(api_client, admin):
    login(api_client, admin.email)
    headers = ["student_id", "student_number", *STUDENT_HEADERS[1:]]
    content = build_workbook(default_sheets(student_headers=headers))

    response = api_client.post(INSPECT_URL, {"file": upload(content)}, format="multipart")

    assert response.status_code == 200
    suggestion = response.json()["sheets"][0]["suggested_mapping"]
    assert "student_id" not in suggestion  # two columns claim the same field


def test_inspect_rejects_a_non_excel_file(api_client, admin):
    login(api_client, admin.email)

    response = api_client.post(
        INSPECT_URL,
        {"file": upload(b"student_id,email\n1,a@b.c\n", name="roster.csv")},
        format="multipart",
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "xlsx" in error["message"]


def test_inspect_rejects_a_corrupt_zip_without_crashing(api_client, admin):
    login(api_client, admin.email)

    response = api_client.post(
        INSPECT_URL, {"file": upload(b"PK\x03\x04broken")}, format="multipart"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# ── Validate / preview ────────────────────────────────────────────────────


def test_validate_previews_without_writing_anything(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            students=[student_row(), student_row("40211235", "ali@example.edu", first="علی")],
            passed=[["40211234", "CS102", 18, PAST_TERM]],
            enrollments=[["40211235", "CS101", "01", CURRENT_TERM]],
        )
    )

    response = validate(
        api_client,
        content,
        mapping_json(passed=PASSED_HEADERS, enrollments=ENROLL_HEADERS),
    )

    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["students_total"] == 2
    assert report["summary"]["will_create"] == 2
    assert report["summary"]["passed_valid"] == 1
    assert report["summary"]["enrollments_valid"] == 1
    assert report["errors"] == []
    assert not User.objects.filter(email="sara@example.edu").exists()
    assert StudentProfile.objects.count() == 0


def test_validate_reports_row_errors_and_keeps_other_rows_valid(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            students=[
                student_row(),
                student_row("40211235", "bad@example.edu", department="UNKNOWN"),
            ]
        )
    )

    response = validate(api_client, content, mapping_json())

    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["students_valid"] == 1
    assert report["summary"]["students_invalid"] == 1
    issue = errors_by_code(report, "INVALID_DEPARTMENT")[0]
    assert issue["sheet"] == "Students" and issue["row"] == 3
    assert issue["field"] == "department"


@pytest.mark.parametrize(
    ("row", "code"),
    [
        (student_row("", "empty@example.edu"), "REQUIRED"),
        (student_row("40211234", "not-an-email"), "INVALID_EMAIL"),
        (student_row("40211234", "a@b.c", degree="دکتری افتخاری"), "INVALID_DEGREE"),
        (student_row("40211234", "a@b.c", entry_year="1200"), "INVALID_ENTRY_YEAR"),
        (student_row("40211234", "a@b.c", current_term="99"), "INVALID_CURRENT_TERM"),
        (student_row("40211234", "a@b.c", gpa="25"), "INVALID_GPA"),
        (student_row("40-211234", "a@b.c"), "INVALID_FORMAT"),
    ],
)
def test_validate_student_field_rules(api_client, admin, catalog, row, code):
    login(api_client, admin.email)
    content = build_workbook(default_sheets(students=[row]))

    report = validate(api_client, content, mapping_json()).json()

    assert errors_by_code(report, code), report["errors"]
    assert report["summary"]["will_create"] == 0


def test_validate_detects_duplicate_rows_inside_the_file(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            students=[student_row(), student_row("40211234", "other@example.edu")],
            passed=[
                ["40211234", "CS101", 18, PAST_TERM],
                ["40211234", "CS101", 19, PAST_TERM],
            ],
        )
    )

    report = validate(
        api_client,
        content,
        mapping_json(passed=PASSED_HEADERS),
    ).json()

    duplicate_issues = errors_by_code(report, "DUPLICATE_IN_FILE")
    assert len(duplicate_issues) == 2  # student number + passed course
    assert report["summary"]["duplicate_rows"] == 2


def test_existing_student_is_skipped_by_default_and_updated_on_request(
    api_client, admin, catalog
):
    login(api_client, admin.email)
    user = make_user("sara@example.edu", Role.STUDENT, first_name="سارا", last_name="محمدی")
    profile = StudentProfile.objects.create(
        user=user,
        student_number="40211234",
        department=catalog["computer"],
        faculty=catalog["faculty"],
        degree_level=DegreeLevel.BACHELOR,
        entry_year="1402",
        current_term_number=3,
        current_gpa="15.00",
    )
    content = build_workbook(default_sheets(students=[student_row(gpa="17.66")]))

    preview = validate(api_client, content, mapping_json()).json()
    assert preview["summary"]["will_skip"] == 1
    assert any(item["code"] == "EXISTING_STUDENT" for item in preview["warnings"])

    upsert = validate(api_client, content, mapping_json(), mode="upsert").json()
    assert upsert["summary"]["will_update"] == 1
    change = upsert["students"][0]["changes"]
    assert any(item["field"] == "current_gpa" and item["to"] == "17.66" for item in change)
    profile.refresh_from_db()
    assert str(profile.current_gpa) == "15.00"  # preview wrote nothing


def test_validate_refuses_a_student_number_belonging_to_another_account(
    api_client, admin, catalog
):
    login(api_client, admin.email)
    other = make_user("other@example.edu", Role.STUDENT)
    StudentProfile.objects.create(
        user=other, student_number="40211234", department=catalog["computer"]
    )
    content = build_workbook(default_sheets(students=[student_row()]))

    report = validate(api_client, content, mapping_json()).json()

    assert errors_by_code(report, "DUPLICATE_STUDENT_NUMBER")


def test_validate_refuses_an_email_owned_by_a_non_student(api_client, admin, catalog):
    login(api_client, admin.email)
    make_user("sara@example.edu", Role.PROFESSOR)
    content = build_workbook(default_sheets(students=[student_row()]))

    report = validate(api_client, content, mapping_json()).json()

    assert errors_by_code(report, "EMAIL_NOT_STUDENT")


def test_validate_rejects_unknown_course_and_term(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(passed=[["40211234", "NOPE", 18, "ترم ناموجود"]])
    )

    report = validate(api_client, content, mapping_json(passed=PASSED_HEADERS)).json()

    assert errors_by_code(report, "UNKNOWN_COURSE")
    assert errors_by_code(report, "INVALID_TERM")


def test_validate_rejects_a_passed_course_in_the_current_term(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(passed=[["40211234", "CS102", 18, CURRENT_TERM]])
    )

    report = validate(api_client, content, mapping_json(passed=PASSED_HEADERS)).json()

    assert errors_by_code(report, "PASSED_IN_CURRENT_TERM")


def test_validate_rejects_passed_and_current_for_the_same_course(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            passed=[["40211234", "CS102", 18, PAST_TERM]],
            enrollments=[["40211234", "CS102", "02", CURRENT_TERM]],
        )
    )

    report = validate(
        api_client,
        content,
        mapping_json(passed=PASSED_HEADERS, enrollments=ENROLL_HEADERS),
    ).json()

    assert errors_by_code(report, "CONFLICT_PASSED_CURRENT")


def test_validate_rejects_an_already_passed_course_as_a_current_enrollment(
    api_client, admin, catalog
):
    login(api_client, admin.email)
    user = make_user("sara@example.edu", Role.STUDENT)
    profile = StudentProfile.objects.create(
        user=user, student_number="40211234", department=catalog["computer"]
    )
    Enrollment.objects.create(
        student=profile,
        course_offering=catalog["offerings"]["cs2_current"],
        status=EnrollmentStatus.PASSED,
        grade="18.00",
    )
    content = build_workbook(
        default_sheets(enrollments=[["40211234", "CS102", "02", CURRENT_TERM]])
    )

    report = validate(
        api_client,
        content,
        mapping_json(enrollments=ENROLL_HEADERS),
        mode="upsert",
    ).json()

    assert errors_by_code(report, "CONFLICT_PASSED_CURRENT")


def test_validate_rejects_an_offering_that_does_not_exist(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(enrollments=[["40211234", "CS101", "99", CURRENT_TERM]])
    )

    report = validate(
        api_client, content, mapping_json(enrollments=ENROLL_HEADERS)
    ).json()

    assert errors_by_code(report, "UNKNOWN_OFFERING")


def test_validate_requires_the_students_sheet(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets(passed=[["40211234", "CS101", 18, PAST_TERM]]))
    mapping = json.dumps(
        {
            "sheets": [
                {
                    "role": "passed_courses",
                    "sheet": "PassedCourses",
                    "columns": {name: name for name in PASSED_HEADERS},
                }
            ]
        }
    )

    response = validate(api_client, content, mapping)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_validate_rejects_an_unknown_mode(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets())

    response = validate(api_client, content, mapping_json(), mode="overwrite_everything")

    assert response.status_code == 400


def test_validate_rejects_a_missing_column_mapping(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets())
    broken = mapping_json(students=STUDENT_HEADERS[1:])

    response = validate(api_client, content, broken)

    assert response.status_code == 400
    assert "کد دانشجویی" in response.json()["error"]["message"]


def test_preview_never_contains_passwords(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets())

    response = validate(api_client, content, mapping_json())

    assert "password" not in response.content.decode("utf-8")


# ── Confirm / execute ─────────────────────────────────────────────────────


def test_confirm_requires_the_validated_bytes(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets())

    response = confirm(api_client, content, mapping_json(), expected_hash="0" * 64)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert not User.objects.filter(email="sara@example.edu").exists()


def test_confirm_requires_an_explicit_confirmation_flag(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets())

    response = confirm(api_client, content, mapping_json(), confirm_flag=False)

    assert response.status_code == 400
    assert not User.objects.filter(email="sara@example.edu").exists()


def test_confirm_creates_accounts_history_and_an_audit_trail(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            students=[student_row(), student_row("40211235", "ali@example.edu", first="علی")],
            passed=[["40211234", "CS102", 18.5, PAST_TERM]],
            enrollments=[["40211235", "CS101", "01", CURRENT_TERM]],
        )
    )
    mapping = mapping_json(passed=PASSED_HEADERS, enrollments=ENROLL_HEADERS)

    response = confirm(api_client, content, mapping)

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["created"] == 2
    assert body["summary"]["passed_imported"] == 1
    assert body["summary"]["enrollments_imported"] == 1

    sara = User.objects.get(email="sara@example.edu")
    assert sara.role == Role.STUDENT
    assert sara.check_password(TEST_PASSWORD) is False
    assert sara.password.startswith("argon2")  # hashed, never plaintext
    profile = sara.student_profile
    assert profile.student_number == "40211234"
    assert profile.department_id == catalog["computer"].pk
    assert profile.degree_level == DegreeLevel.BACHELOR
    assert profile.entry_year == "1402"
    assert profile.current_term_number == 3
    assert str(profile.current_gpa) == "17.66"

    passed = Enrollment.objects.get(student=profile, status=EnrollmentStatus.PASSED)
    assert passed.course_offering.course.code == "CS102"
    assert str(passed.grade) == "18.50"

    ali = User.objects.get(email="ali@example.edu").student_profile
    enrolled = Enrollment.objects.get(student=ali)
    assert enrolled.status == EnrollmentStatus.ENROLLED
    assert enrolled.course_offering == catalog["offerings"]["cs1_current"]

    audit = AuditLog.objects.get(entity_type="student_import")
    assert audit.actor == admin
    assert audit.metadata["summary"]["created"] == 2
    serialized = json.dumps(audit.metadata, ensure_ascii=False)
    assert "password" not in serialized
    assert "sara@example.edu" not in serialized  # masked in metadata


def test_confirm_creates_a_closed_historical_offering_when_missing(api_client, admin, catalog):
    login(api_client, admin.email)
    # MATH101 has no past offering at all.
    content = build_workbook(
        default_sheets(passed=[["40211234", "MATH101", 16, PAST_TERM]])
    )

    response = confirm(api_client, content, mapping_json(passed=PASSED_HEADERS))

    assert response.status_code == 200
    offering = CourseOffering.objects.get(course=catalog["math1"], term=catalog["past"])
    assert offering.section_code == "01"
    assert offering.capacity == 0
    assert offering.status == OfferingStatus.CLOSED


def test_confirm_reports_generated_passwords_exactly_once(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            students=[student_row(), student_row("40211235", "ali@example.edu", first="علی")]
        )
    )

    body = confirm(api_client, content, mapping_json()).json()

    credentials = body["created_credentials"]
    assert len(credentials) == 2
    passwords = {item["password"] for item in credentials}
    assert len(passwords) == 2  # never one shared default
    assert all(len(value) >= 12 for value in passwords)

    # The generated password really works for the imported student.
    api_client.credentials()
    login(api_client, "sara@example.edu", credentials[0]["password"])
    me = api_client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.json()["email"] == "sara@example.edu"


def test_confirm_skips_existing_students_and_never_deletes_history(api_client, admin, catalog):
    login(api_client, admin.email)
    user = make_user("sara@example.edu", Role.STUDENT, first_name="سارا")
    profile = StudentProfile.objects.create(
        user=user,
        student_number="40211234",
        department=catalog["computer"],
        degree_level=DegreeLevel.BACHELOR,
        entry_year="1400",
        current_gpa="12.00",
    )
    old = Enrollment.objects.create(
        student=profile,
        course_offering=catalog["offerings"]["cs1_past"],
        status=EnrollmentStatus.PASSED,
        grade="14.00",
    )
    content = build_workbook(
        default_sheets(
            passed=[["40211234", "CS102", 18, PAST_TERM]],
            enrollments=[["40211234", "CS101", "01", CURRENT_TERM]],
        )
    )

    response = confirm(
        api_client,
        content,
        mapping_json(passed=PASSED_HEADERS, enrollments=ENROLL_HEADERS),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["skipped"] == 1
    assert body["summary"]["passed_imported"] == 0
    profile.refresh_from_db()
    assert profile.entry_year == "1400"  # untouched in create-only mode
    assert str(profile.current_gpa) == "12.00"
    old.refresh_from_db()
    assert str(old.grade) == "14.00"
    # The skipped student gains no new history from this file.
    assert Enrollment.objects.filter(student=profile).count() == 1


def test_confirm_upsert_updates_profile_but_keeps_existing_history(api_client, admin, catalog):
    login(api_client, admin.email)
    user = make_user("sara@example.edu", Role.STUDENT)
    profile = StudentProfile.objects.create(
        user=user,
        student_number="40211234",
        department=catalog["computer"],
        degree_level=DegreeLevel.BACHELOR,
        entry_year="1400",
        current_gpa="12.00",
    )
    old = Enrollment.objects.create(
        student=profile,
        course_offering=catalog["offerings"]["cs1_past"],
        status=EnrollmentStatus.PASSED,
        grade="14.00",
    )
    content = build_workbook(
        default_sheets(
            students=[student_row(gpa="16.50", current_term="5")],
            passed=[["40211234", "CS102", 18, PAST_TERM]],
        )
    )

    response = confirm(
        api_client,
        content,
        mapping_json(passed=PASSED_HEADERS),
        mode="upsert",
    )

    assert response.status_code == 200
    profile.refresh_from_db()
    assert str(profile.current_gpa) == "16.50"
    assert profile.current_term_number == 5
    old.refresh_from_db()
    assert str(old.grade) == "14.00"  # never overwritten
    assert Enrollment.objects.filter(student=profile).count() == 2


def test_confirm_is_idempotent(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            passed=[["40211234", "CS102", 18, PAST_TERM]],
            enrollments=[["40211234", "CS101", "01", CURRENT_TERM]],
        )
    )
    mapping = mapping_json(passed=PASSED_HEADERS, enrollments=ENROLL_HEADERS)

    first = confirm(api_client, content, mapping).json()
    second = confirm(api_client, content, mapping).json()

    assert first["summary"]["created"] == 1
    assert first["summary"]["passed_imported"] == 1
    assert second["summary"]["skipped"] == 1
    assert second["summary"]["created"] == 0
    assert second["summary"]["passed_imported"] == 0
    assert second["summary"]["enrollments_imported"] == 0
    profile = User.objects.get(email="sara@example.edu").student_profile
    assert Enrollment.objects.filter(student=profile).count() == 2


def test_confirm_partially_imports_valid_rows(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(
            students=[
                student_row(),
                student_row("40211235", "bad@example.edu", department="UNKNOWN"),
            ]
        )
    )

    response = confirm(api_client, content, mapping_json())

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["created"] == 1
    assert body["summary"]["failed"] == 1
    assert User.objects.filter(email="sara@example.edu").exists()
    assert not User.objects.filter(email="bad@example.edu").exists()
    assert errors_by_code(body, "INVALID_DEPARTMENT")


def test_confirm_rejects_a_file_with_no_valid_student(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(
        default_sheets(students=[student_row("40211234", "bad@example.edu", department="UNKNOWN")])
    )

    response = confirm(api_client, content, mapping_json())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_confirm_upgrades_a_planned_course_to_enrolled(api_client, admin, catalog):
    login(api_client, admin.email)
    user = make_user("sara@example.edu", Role.STUDENT)
    profile = StudentProfile.objects.create(
        user=user, student_number="40211234", department=catalog["computer"]
    )
    planned = Enrollment.objects.create(
        student=profile,
        course_offering=catalog["offerings"]["cs2_current"],
        status=EnrollmentStatus.PLANNED,
    )
    content = build_workbook(
        default_sheets(enrollments=[["40211234", "CS102", "02", CURRENT_TERM]])
    )

    response = confirm(
        api_client,
        content,
        mapping_json(enrollments=ENROLL_HEADERS),
        mode="upsert",
    )

    assert response.status_code == 200
    planned.refresh_from_db()
    assert planned.status == EnrollmentStatus.ENROLLED
    assert response.json()["summary"]["enrollments_imported"] == 1


# ── Reports ───────────────────────────────────────────────────────────────


def test_reports_endpoint_lists_import_summaries(api_client, admin, catalog):
    login(api_client, admin.email)
    content = build_workbook(default_sheets())
    confirm(api_client, content, mapping_json())

    response = api_client.get(REPORTS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    row = body["results"][0]
    assert row["actor"] == admin.email
    assert row["mode"] == "create_only"
    assert row["summary"]["created"] == 1
    assert len(row["file_hash"]) == 64
    assert "password" not in json.dumps(body)


def test_reports_are_admin_only(api_client, student):
    login(api_client, student.email)
    assert api_client.get(REPORTS_URL).status_code == 403
