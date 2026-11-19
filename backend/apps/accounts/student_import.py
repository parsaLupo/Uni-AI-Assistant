"""Bulk student import — parse → map → validate → preview → execute.

Feature location: Admin → Users → «افزودن گروهی دانشجویان» (docs/api/admin.md).
The pipeline is deterministic backend rules (AGENTS.md §8); the workbook is
untrusted input (§9): it is read with ``read_only=True, data_only=True`` so
formulas are never executed (cached values only) and macros never run.

Design notes
------------
* **Stateless.** The admin's file is re-uploaded on validate *and* confirm;
  ``sha256`` of the bytes pins the exact workbook they previewed, so the
  confirm cannot silently import different data. Nothing is stored server-side
  between steps.
* **Template and exports share one pipeline.** ``parse_workbook`` +
  ``resolve_mapping`` + ``validate_import`` are the only entry points; the
  standard template is simply a workbook whose headers the suggester maps.
* **Reuse, not duplication.** Users are created through ``User.objects``
  (email identity, Argon2id hashing), profiles through ``StudentProfile``,
  history through the existing ``Enrollment`` + PASSED status. When a passed
  course has no historical offering, the same convention as the existing
  academic-history path applies: a closed section-01 offering (capacity 0) is
  created — additive only, never touching real offerings.
* **Safety.** Existing students are skipped unless the admin selects update
  mode; academic history is never overwritten, and nothing is deleted because
  it is absent from a file. Each student is imported in its own transaction
  (a bad row cannot leave half a student), while unrelated valid rows still
  import.
"""

from __future__ import annotations

import hashlib
import io
import logging
import secrets
import string
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from apps.academics.models import AcademicTerm, Department
from apps.accounts.models import Role, User
from apps.analytics.models import AuditAction, AuditLog
from apps.common.errors import VALIDATION_ERROR, ApiError
from apps.common.persian import normalize_persian
from apps.courses.models import Course, CourseOffering, OfferingStatus
from apps.students.models import DegreeLevel, Enrollment, EnrollmentStatus, StudentProfile

logger = logging.getLogger("app.accounts.student_import")

# ── Limits and constants ──────────────────────────────────────────────────

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB — an academic roster is far smaller.
MAX_ROWS_PER_SHEET = 5000

SHEET_INSTRUCTIONS = "راهنما"
# Titles that mark a human-readable guide, never a data sheet.
INSTRUCTION_SHEET_KEYS = ("راهنما", "دستورالعمل", "instructions", "guide", "readme")
SHEET_STUDENTS = "Students"
SHEET_PASSED = "PassedCourses"
SHEET_ENROLLMENTS = "CurrentEnrollments"

ROLE_STUDENTS = "students"
ROLE_PASSED = "passed_courses"
ROLE_ENROLLMENTS = "current_enrollments"

ROLE_LABELS = {
    ROLE_STUDENTS: "فهرست دانشجویان",
    ROLE_PASSED: "دروس پاس‌شده",
    ROLE_ENROLLMENTS: "ثبت‌نام ترم جاری",
}

MODE_CREATE_ONLY = "create_only"
MODE_UPSERT = "upsert"
MODES = {MODE_CREATE_ONLY, MODE_UPSERT}

STUDENT_FIELDS = (
    "student_id",
    "first_name",
    "last_name",
    "email",
    "department",
    "degree",
    "entry_year",
    "current_term",
    "gpa",
)
PASSED_FIELDS = ("student_id", "course_code", "grade", "term")
ENROLLMENT_FIELDS = ("student_id", "course_code", "group_code", "term")

REQUIRED_STUDENT_FIELDS = (
    "student_id",
    "first_name",
    "last_name",
    "email",
    "department",
    "degree",
    "entry_year",
)
REQUIRED_PASSED_FIELDS = ("student_id", "course_code", "grade", "term")
REQUIRED_ENROLLMENT_FIELDS = ("student_id", "course_code", "group_code", "term")

FIELD_LABELS = {
    "student_id": "کد دانشجویی",
    "first_name": "نام",
    "last_name": "نام خانوادگی",
    "email": "ایمیل",
    "department": "گروه آموزشی (رشته)",
    "degree": "مقطع",
    "entry_year": "سال ورود",
    "current_term": "شماره ترم جاری",
    "gpa": "معدل",
    "course_code": "کد درس",
    "grade": "نمره",
    "term": "ترم",
    "group_code": "شماره گروه",
}

# Header synonyms, compared after ``normalize_persian`` (which removes all
# whitespace/punctuation and folds case), so «Student Number», «student_number»
# and «شماره دانشجویی» all collapse to one key.
HEADER_SYNONYMS: dict[str, tuple[str, ...]] = {
    "student_id": (
        "student_id",
        "studentid",
        "student_number",
        "studentnumber",
        "student_no",
        "studentno",
        "studentcode",
        "id",
        "کددانشجویی",
        "شمارهدانشجویی",
        "شمارهدانشجو",
        "کددانشجو",
    ),
    "first_name": ("first_name", "firstname", "name", "givenname", "نام", "نامکوچک"),
    "last_name": (
        "last_name",
        "lastname",
        "family",
        "surname",
        "familyname",
        "نامخانوادگی",
        "خانوادگی",
        "فامیل",
    ),
    "email": ("email", "emailaddress", "ایمیل", "پستالکترونیک", "رایانامه", "پست الکترونیک"),
    "department": (
        "department",
        "major",
        "field",
        "group",
        "رشته",
        "رشتهتحصیلی",
        "گروه",
        "گروهآموزشی",
        "گروهرشتهایدرس",
    ),
    "degree": (
        "degree",
        "degreelevel",
        "level",
        "مقطع",
        "مقطعتحصیلی",
        "سطح",
        "دوره",
    ),
    "entry_year": (
        "entry_year",
        "entryyear",
        "admissionyear",
        "yearofentry",
        "سالورود",
        "سالپذیرش",
        "سالقبولیترمورود",
    ),
    "current_term": (
        "current_term",
        "currentterm",
        "termnumber",
        "currentterm_number",
        "ترمجاری",
        "ترمفعلی",
        "شمارهترم",
    ),
    "gpa": ("gpa", "cgpa", "average", "معدل", "معدلکل", "میانگین", "میانگیننمرات"),
    "course_code": (
        "course_code",
        "coursecode",
        "courseno",
        "coursenumber",
        "کددرس",
        "شمارهدرس",
        "کددوره",
    ),
    "grade": ("grade", "score", "finalgrade", "نمره", "نمرهنهایی", "امتیاز"),
    "term": ("term", "semester", "ترم", "نیمسال", "ترمتحصیلی", "نیمسالتحصیلی"),
    "group_code": (
        "group_code",
        "groupcode",
        "section",
        "sectioncode",
        "group",
        "گروه",
        "شمارهگروه",
        "کدگروه",
    ),
}

# Persian degree labels → the model's enum values.
DEGREE_LABELS = {
    "bachelor": DegreeLevel.BACHELOR,
    "bachelors": DegreeLevel.BACHELOR,
    "کارشناسی": DegreeLevel.BACHELOR,
    "کارشناسي": DegreeLevel.BACHELOR,
    "کارشناسیپیوسته": DegreeLevel.BACHELOR,
    "master": DegreeLevel.MASTER,
    "masters": DegreeLevel.MASTER,
    "کارشناسیارشد": DegreeLevel.MASTER,
    "ارشد": DegreeLevel.MASTER,
    "phd": DegreeLevel.PHD,
    "doctorate": DegreeLevel.PHD,
    "دکتری": DegreeLevel.PHD,
    "دکترا": DegreeLevel.PHD,
    "دکتریتخصصی": DegreeLevel.PHD,
}

# Field state translation for *display* values (normalize_persian strips all
# whitespace, which must never happen to names).
_VALUE_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٫": ".",
        "٬": "",
        "\u200c": " ",
    }
)


# ── Errors and small helpers ──────────────────────────────────────────────


@dataclass
class Issue:
    """One row-level validation finding (shown with sheet + row + field)."""

    sheet: str
    row: int
    field: str
    code: str
    message: str

    def to_dict(self) -> dict:
        return {
            "sheet": self.sheet,
            "row": self.row,
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


def _text(value: Any) -> str:
    """Cell → display text: digits/letters normalised, whitespace collapsed."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    out = str(value).translate(_VALUE_TRANSLATION).replace("\u00a0", " ")
    return " ".join(out.split())


def _digits(value: Any) -> str:
    """Cell → ASCII-digit string (Persian/Arabic digits included)."""
    return _text(value).replace(" ", "")


def _decimal(value: Any) -> Decimal | None:
    raw = _digits(value).replace("٬", "").replace(",", "")
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _header_key(value: Any) -> str:
    """Comparison key for headers (matches ``normalize_persian`` output)."""
    return normalize_persian(_text(value))


def _mask_email(email: str) -> str:
    """Never echo full addresses in audit metadata."""
    local, _, domain = email.partition("@")
    if not local:
        return email
    return f"{local[:2]}***@{domain}" if domain else f"{local[:2]}***"


def _generate_password() -> str:
    """Unique password per imported student (never a shared default)."""
    alphabet = string.ascii_letters + string.digits
    symbols = "!@#$%^&*-_=+"
    for _ in range(50):
        core = "".join(secrets.choice(alphabet) for _ in range(10))
        password = (
            secrets.choice(string.ascii_uppercase)
            + secrets.choice(string.ascii_lowercase)
            + secrets.choice(string.digits)
            + secrets.choice(symbols)
            + core
        )
        try:
            validate_password(password)
        except DjangoValidationError:
            continue
        return password
    # Practically unreachable; never fall back to a predictable default.
    raise ApiError(
        VALIDATION_ERROR,
        "تولید گذرواژهٔ امن برای حساب‌های جدید ممکن نشد؛ دوباره تلاش کنید.",
        http_status=500,
    )


# ── Template generation ───────────────────────────────────────────────────


def _style_header(sheet: Worksheet, columns: int) -> None:
    fill = PatternFill("solid", fgColor="DDE7F5")
    for index in range(1, columns + 1):
        cell = sheet.cell(row=1, column=index)
        cell.font = Font(bold=True)
        cell.fill = fill
        sheet.column_dimensions[get_column_letter(index)].width = 24


def build_template_workbook() -> bytes:
    """The downloadable official template (4 sheets, Persian instructions)."""
    workbook = Workbook()

    instructions = workbook.active
    instructions.title = SHEET_INSTRUCTIONS
    instructions.append(["راهنمای بارگذاری گروهی دانشجویان"])
    instructions["A1"].font = Font(bold=True, size=14)
    instructions.append([])
    instructions.append(
        ["این فایل سه برگهٔ داده و همین برگهٔ راهنما دارد. سطر اول هر برگه سرستون است."]
    )
    instructions.append(
        [
            "دانشجوی موجود (کد دانشجویی یا ایمیل) به‌طور پیش‌فرض نادیده گرفته می‌شود؛ "
            "برای به‌روزرسانی، در پیش‌نمایش گزینهٔ به‌روزرسانی را انتخاب کنید."
        ]
    )
    instructions.append(["هیچ سابقهٔ تحصیلی حذف یا بازنویسی نمی‌شود؛ فقط رکورد جدید افزوده می‌شود."])
    instructions.append(
        ["برای هر دانشجوی جدید، گذرواژهٔ یکتا پس از واردکردن نمایش داده می‌شود و باید امن تحویل شود."]
    )
    instructions.append([])

    rows = [
        ("برگه", "ستون", "الزامی", "نوع/مثال", "توضیح"),
        ("Students", "student_id", "بله", "40211234", "کد دانشجویی؛ یکتا در کل سامانه"),
        ("Students", "first_name", "بله", "سارا", "نام"),
        ("Students", "last_name", "بله", "محمدی", "نام خانوادگی"),
        ("Students", "email", "بله", "sara@example.ac.ir", "ایمیل حساب؛ شناسهٔ یکتای ورود"),
        ("Students", "department", "بله", "مهندسی کامپیوتر", "گروه آموزشی موجود در سامانه"),
        ("Students", "degree", "بله", "کارشناسی / کارشناسی ارشد / دکتری", "مقطع تحصیلی"),
        ("Students", "entry_year", "بله", "1402", "سال ورود شمسی (۱۳۵۰ تا ۱۴۲۰)"),
        ("Students", "current_term", "خیر", "3", "شمارهٔ ترم جاری (عدد ۱ تا ۲۰)"),
        ("Students", "gpa", "خیر", "17.66", "معدل در بازهٔ ۰ تا ۲۰"),
        ("PassedCourses", "student_id", "بله", "40211234", "کد دانشجویی موجود در فایل یا سامانه"),
        ("PassedCourses", "course_code", "بله", "1916003", "کد درس موجود در سرفصل"),
        ("PassedCourses", "grade", "بله", "18.5", "نمرهٔ نهایی در بازهٔ ۰ تا ۲۰"),
        ("PassedCourses", "term", "بله", "نیمسال اول 1404-1405", "نام کامل ترم گذشته در سامانه"),
        ("CurrentEnrollments", "student_id", "بله", "40211234", "کد دانشجویی"),
        ("CurrentEnrollments", "course_code", "بله", "1916010", "کد درس"),
        ("CurrentEnrollments", "group_code", "بله", "01", "شمارهٔ گروه ارائهٔ همان درس و ترم"),
        ("CurrentEnrollments", "term", "بله", "نیمسال اول 1405-1406", "ترم ارائهٔ همان درس و گروه"),
    ]
    for row in rows:
        instructions.append(list(row))
    for index in range(1, 6):
        instructions.cell(row=1, column=index).font = Font(bold=True)
    instructions.column_dimensions["A"].width = 22
    instructions.column_dimensions["B"].width = 22
    instructions.column_dimensions["C"].width = 10
    instructions.column_dimensions["D"].width = 34
    instructions.column_dimensions["E"].width = 60

    students = workbook.create_sheet(SHEET_STUDENTS)
    students.append([*STUDENT_FIELDS])
    _style_header(students, len(STUDENT_FIELDS))

    passed = workbook.create_sheet(SHEET_PASSED)
    passed.append([*PASSED_FIELDS])
    _style_header(passed, len(PASSED_FIELDS))

    enrollments = workbook.create_sheet(SHEET_ENROLLMENTS)
    enrollments.append([*ENROLLMENT_FIELDS])
    _style_header(enrollments, len(ENROLLMENT_FIELDS))

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ── Workbook parsing ──────────────────────────────────────────────────────


def validate_file_bytes(data: bytes) -> None:
    """Reject oversized / non-xlsx uploads before openpyxl touches them."""
    if not data:
        raise ApiError(VALIDATION_ERROR, "فایلی انتخاب نشده است.", http_status=400)
    if len(data) > MAX_FILE_BYTES:
        raise ApiError(
            VALIDATION_ERROR,
            "حجم فایل بیش از حد مجاز است (حداکثر ۵ مگابایت).",
            http_status=400,
        )
    if not data.startswith(b"PK"):
        raise ApiError(
            VALIDATION_ERROR,
            "فایل باید از نوع Excel با پسوند .xlsx باشد.",
            http_status=400,
        )
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:  # pragma: no cover - defensive
        raise ApiError(VALIDATION_ERROR, "فایل Excel معتبر نیست.", http_status=400) from exc
    if "xl/workbook.xml" not in names:
        raise ApiError(
            VALIDATION_ERROR,
            "فایل باید از نوع Excel با پسوند .xlsx باشد (ساختار امن پیدا نشد).",
            http_status=400,
        )


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class ParsedSheet:
    name: str
    header_row: int
    headers: list[str]
    rows: list[tuple[int, list[Any]]]  # (excel row number, cell values)

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class ParsedWorkbook:
    hash: str
    sheets: dict[str, ParsedSheet]


def parse_workbook(data: bytes) -> ParsedWorkbook:
    """Parse an uploaded workbook into header + raw rows per non-empty sheet."""
    validate_file_bytes(data)
    try:
        workbook = load_workbook(
            io.BytesIO(data), read_only=True, data_only=True, keep_links=False
        )
    except Exception as exc:  # noqa: BLE001 - corrupt file from untrusted input
        raise ApiError(
            VALIDATION_ERROR,
            "خواندن فایل Excel ممکن نشد؛ از سالم‌بودن فایل مطمئن شوید.",
            http_status=400,
        ) from exc

    sheets: dict[str, ParsedSheet] = {}
    try:
        for sheet in workbook.worksheets:
            key = _header_key(sheet.title)
            if any(key.startswith(marker) for marker in INSTRUCTION_SHEET_KEYS):
                continue  # guide sheet, not registrar data
            parsed = _parse_sheet(sheet)
            if parsed is not None:
                sheets[sheet.title] = parsed
    finally:
        workbook.close()
    if not sheets:
        raise ApiError(VALIDATION_ERROR, "هیچ برگهٔ داده‌ای در فایل پیدا نشد.", http_status=400)
    return ParsedWorkbook(hash=file_hash(data), sheets=sheets)


def _parse_sheet(sheet: Worksheet) -> ParsedSheet | None:
    rows = sheet.iter_rows(values_only=True)
    header_values: list[Any] | None = None
    header_row = 1
    data_rows: list[tuple[int, list[Any]]] = []
    row_number = 0
    for row in rows:
        row_number += 1
        values = list(row)
        if header_values is None:
            if all(_text(value) == "" for value in values):
                continue  # leading empty rows
            header_values = values
            header_row = row_number
            continue
        if all(_text(value) == "" for value in values):
            continue
        if len(data_rows) >= MAX_ROWS_PER_SHEET:
            raise ApiError(
                VALIDATION_ERROR,
                f"سطرهای برگهٔ «{sheet.title}» بیش از حد مجاز است "
                f"(حداکثر {MAX_ROWS_PER_SHEET}).",
                http_status=400,
            )
        data_rows.append((row_number, values))
    if header_values is None or not data_rows:
        return None
    headers = [_text(value) for value in header_values]
    # Trim trailing empty header cells.
    while headers and headers[-1] == "":
        headers.pop()
    if not headers:
        return None
    return ParsedSheet(
        name=sheet.title,
        header_row=header_row,
        headers=headers,
        rows=data_rows,
    )


# ── Mapping suggestions ───────────────────────────────────────────────────


def _normalized_synonyms(field_name: str) -> set[str]:
    return {normalize_persian(item) for item in HEADER_SYNONYMS[field_name]}


def _header_index(parsed: ParsedSheet) -> dict[str, int]:
    """First index per normalised header; duplicates keep the first."""
    index: dict[str, int] = {}
    for position, header in enumerate(parsed.headers):
        key = _header_key(header)
        if key and key not in index:
            index[key] = position
    return index


def suggest_mapping(parsed: ParsedSheet, fields: Iterable[str]) -> dict[str, str]:
    """Unambiguous field → header text suggestions only (never a guess)."""
    index = _header_index(parsed)
    suggestions: dict[str, str] = {}
    used_positions: set[int] = set()
    for field_name in fields:
        matches = [
            key for key in _normalized_synonyms(field_name) if key in index
        ]
        positions = {index[key] for key in matches}
        if len(positions) != 1:
            continue  # no match, or two different headers claim the field
        position = positions.pop()
        if position in used_positions:
            continue  # two fields would share one header — leave to the admin
        used_positions.add(position)
        suggestions[field_name] = parsed.headers[position]
    return suggestions


def _role_fields(role: str) -> tuple[str, ...]:
    return {
        ROLE_STUDENTS: STUDENT_FIELDS,
        ROLE_PASSED: PASSED_FIELDS,
        ROLE_ENROLLMENTS: ENROLLMENT_FIELDS,
    }[role]


def suggest_role(parsed: ParsedSheet) -> str | None:
    """Suggest the logical role only when every required field maps cleanly."""
    best: tuple[int, str] | None = None
    for role in (ROLE_STUDENTS, ROLE_PASSED, ROLE_ENROLLMENTS):
        suggestions = suggest_mapping(parsed, _role_fields(role))
        required = {
            ROLE_STUDENTS: REQUIRED_STUDENT_FIELDS,
            ROLE_PASSED: REQUIRED_PASSED_FIELDS,
            ROLE_ENROLLMENTS: REQUIRED_ENROLLMENT_FIELDS,
        }[role]
        if all(field_name in suggestions for field_name in required):
            score = len(suggestions)
            if best is None or score > best[0]:
                best = (score, role)
    return best[1] if best else None


def inspect_workbook(parsed: ParsedWorkbook, sample_size: int = 5) -> dict:
    """Response body of the inspect endpoint: sheets, headers, suggestions."""
    sheets = []
    for parsed_sheet in parsed.sheets.values():
        role = suggest_role(parsed_sheet)
        role_fields = _role_fields(role) if role else STUDENT_FIELDS
        sheets.append(
            {
                "name": parsed_sheet.name,
                "row_count": parsed_sheet.row_count,
                "headers": parsed_sheet.headers,
                "suggested_role": role,
                "suggested_mapping": suggest_mapping(parsed_sheet, role_fields),
                "sample_rows": [
                    [_text(value) for value in values[: len(parsed_sheet.headers)]]
                    for _, values in parsed_sheet.rows[:sample_size]
                ],
            }
        )
    return {"file_hash": parsed.hash, "sheets": sheets}


# ── Mapping resolution ────────────────────────────────────────────────────


@dataclass
class SheetMapping:
    role: str
    sheet: ParsedSheet
    columns: dict[str, int]  # logical field → column index


def resolve_mapping(parsed: ParsedWorkbook, raw_mapping: Any) -> dict[str, SheetMapping]:
    """Validate the admin's mapping payload against the actual workbook."""
    if not raw_mapping or not isinstance(raw_mapping, dict):
        raise ApiError(VALIDATION_ERROR, "نگاشت ستون‌ها ارسال نشده است.", http_status=400)
    raw_sheets = raw_mapping.get("sheets")
    if not isinstance(raw_sheets, list) or not raw_sheets:
        raise ApiError(VALIDATION_ERROR, "برای هر نقش حداقل یک برگه انتخاب کنید.", http_status=400)

    resolved: dict[str, SheetMapping] = {}
    required = {
        ROLE_STUDENTS: REQUIRED_STUDENT_FIELDS,
        ROLE_PASSED: REQUIRED_PASSED_FIELDS,
        ROLE_ENROLLMENTS: REQUIRED_ENROLLMENT_FIELDS,
    }
    for entry in raw_sheets:
        if not isinstance(entry, dict):
            raise ApiError(VALIDATION_ERROR, "ساختار نگاشت نامعتبر است.", http_status=400)
        role = str(entry.get("role") or "")
        if role not in required:
            raise ApiError(VALIDATION_ERROR, "نقش برگه نامعتبر است.", http_status=400)
        if role in resolved:
            raise ApiError(VALIDATION_ERROR, "هر نقش فقط یک بار قابل انتخاب است.", http_status=400)
        sheet_name = str(entry.get("sheet") or "")
        parsed_sheet = parsed.sheets.get(sheet_name)
        if parsed_sheet is None:
            raise ApiError(
                VALIDATION_ERROR,
                f"برگهٔ «{sheet_name}» در فایل پیدا نشد.",
                http_status=400,
            )
        raw_columns = entry.get("columns") or {}
        if not isinstance(raw_columns, dict):
            raise ApiError(VALIDATION_ERROR, "ساختار ستون‌ها نامعتبر است.", http_status=400)
        headers_by_key = {
            _header_key(header): position
            for position, header in enumerate(parsed_sheet.headers)
        }
        columns: dict[str, int] = {}
        for field_name, header_text in raw_columns.items():
            if field_name not in _role_fields(role):
                continue  # unknown fields are ignored, never trusted
            position = headers_by_key.get(_header_key(header_text))
            if position is None:
                raise ApiError(
                    VALIDATION_ERROR,
                    f"ستون «{_text(header_text)}» در برگهٔ «{sheet_name}» پیدا نشد.",
                    http_status=400,
                )
            columns[field_name] = position
        missing = [FIELD_LABELS[name] for name in required[role] if name not in columns]
        if missing:
            raise ApiError(
                VALIDATION_ERROR,
                f"برای برگهٔ «{sheet_name}» این ستون‌ها باید نگاشت شوند: {'، '.join(missing)}",
                http_status=400,
            )
        resolved[role] = SheetMapping(role=role, sheet=parsed_sheet, columns=columns)
    if ROLE_STUDENTS not in resolved:
        raise ApiError(VALIDATION_ERROR, "برگهٔ دانشجویان باید انتخاب شود.", http_status=400)
    return resolved


def _cell(mapping: SheetMapping, values: list[Any], field_name: str) -> Any:
    position = mapping.columns.get(field_name)
    if position is None or position >= len(values):
        return None
    return values[position]


# ── Reference data ────────────────────────────────────────────────────────


@dataclass
class Reference:
    departments_by_code: dict[str, Department] = field(default_factory=dict)
    departments_by_name: dict[str, Department] = field(default_factory=dict)
    courses_by_code: dict[str, Course] = field(default_factory=dict)
    terms_by_name: dict[str, AcademicTerm] = field(default_factory=dict)
    terms_by_year: dict[str, list[AcademicTerm]] = field(default_factory=dict)
    users_by_email: dict[str, User] = field(default_factory=dict)
    profiles_by_number: dict[str, StudentProfile] = field(default_factory=dict)
    current_term: AcademicTerm | None = None
    offerings: dict[tuple[int, int], list[CourseOffering]] = field(default_factory=dict)


def load_reference() -> Reference:
    """Load every lookup table once per validation/execution pass."""
    reference = Reference()
    # Existing accounts/profiles are filled per workbook by
    # ``_populate_existing_students`` (never by loading the whole user table).
    for department in Department.objects.filter(is_active=True).select_related("faculty"):
        reference.departments_by_code[normalize_persian(department.code)] = department
        reference.departments_by_name[normalize_persian(department.name)] = department
    for course in Course.objects.filter(active=True):
        reference.courses_by_code[normalize_persian(course.code)] = course
    for term in AcademicTerm.objects.all():
        reference.terms_by_name[normalize_persian(term.name)] = term
        reference.terms_by_year.setdefault(normalize_persian(term.academic_year), []).append(term)
        if term.is_current:
            reference.current_term = term
    for offering in CourseOffering.objects.select_related("course", "term"):
        reference.offerings.setdefault((offering.course_id, offering.term_id), []).append(offering)
    return reference


def _populate_existing_students(reference: Reference, mapping: SheetMapping) -> None:
    """Batch-load the accounts/profiles the students sheet actually references."""
    numbers: set[str] = set()
    emails: set[str] = set()
    for _, values in mapping.sheet.rows:
        number = _digits(_cell(mapping, values, "student_id"))
        email = _text(_cell(mapping, values, "email")).lower()
        if number:
            numbers.add(number)
        if email:
            emails.add(email)
    if emails:
        for user in User.objects.filter(email__in=emails):
            reference.users_by_email[user.email] = user
    if numbers:
        profiles = StudentProfile.objects.filter(student_number__in=numbers).select_related("user")
        for profile in profiles:
            reference.profiles_by_number[profile.student_number] = profile
            reference.users_by_email.setdefault(profile.user.email, profile.user)


def _match_department(reference: Reference, value: str) -> Department | None:
    key = normalize_persian(value)
    if not key:
        return None
    return reference.departments_by_code.get(key) or reference.departments_by_name.get(key)


def _match_degree(value: str) -> str | None:
    key = normalize_persian(value)
    if not key:
        return None
    for label, level in DEGREE_LABELS.items():
        if normalize_persian(label) == key:
            return level
    return None


def _match_term(reference: Reference, value: str) -> AcademicTerm | None:
    key = normalize_persian(value)
    if not key:
        return None
    term = reference.terms_by_name.get(key)
    if term is not None:
        return term
    by_year = reference.terms_by_year.get(key, [])
    return by_year[0] if len(by_year) == 1 else None


def _match_course(reference: Reference, value: str) -> Course | None:
    return reference.courses_by_code.get(normalize_persian(value))


def _match_offering(
    reference: Reference,
    course: Course,
    term: AcademicTerm,
    group_code: str,
) -> CourseOffering | None:
    candidates = reference.offerings.get((course.pk, term.pk), [])
    if not candidates:
        return None
    wanted = normalize_persian(group_code)
    if wanted:
        for offering in candidates:
            if normalize_persian(offering.section_code) == wanted:
                return offering
        return None
    return sorted(candidates, key=lambda item: item.section_code)[0]


# ── Validation plan ───────────────────────────────────────────────────────


@dataclass
class StudentRow:
    row: int
    student_id: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    department: Department | None = None
    degree: str = ""
    entry_year: str = ""
    current_term: int | None = None
    gpa: Decimal | None = None
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    existing_user: User | None = None
    existing_profile: StudentProfile | None = None
    outcome: str = "create"  # create | update | skip | error
    changes: list[dict] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors and bool(self.student_id) and bool(self.email)

    def to_report(self) -> dict:
        return {
            "row": self.row,
            "student_id": self.student_id,
            "email": self.email,
            "full_name": f"{self.first_name} {self.last_name}".strip(),
            "department": self.department.name if self.department else "",
            "degree": self.degree,
            "entry_year": self.entry_year,
            "current_term": self.current_term,
            "gpa": str(self.gpa) if self.gpa is not None else None,
            "outcome": self.outcome,
            "changes": self.changes,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass
class HistoryRow:
    row: int
    kind: str  # passed | enrollment
    student_id: str = ""
    course_code: str = ""
    course: Course | None = None
    term: AcademicTerm | None = None
    group_code: str = ""
    offering: CourseOffering | None = None
    grade: Decimal | None = None
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.course is not None and self.term is not None

    def to_report(self) -> dict:
        data = {
            "row": self.row,
            "kind": self.kind,
            "student_id": self.student_id,
            "course_code": self.course_code,
            "term": self.term.name if self.term else "",
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }
        if self.kind == "enrollment":
            data["group_code"] = self.group_code
        else:
            data["grade"] = str(self.grade) if self.grade is not None else None
        return data


@dataclass
class ImportPlan:
    workbook_hash: str
    mode: str
    students: list[StudentRow]
    passed_rows: list[HistoryRow]
    enrollment_rows: list[HistoryRow]
    errors: list[Issue]
    warnings: list[Issue]
    duplicate_rows: int = 0

    def valid_students(self) -> list[StudentRow]:
        return [row for row in self.students if row.is_valid and row.outcome != "error"]

    def students_by_number(self) -> dict[str, StudentRow]:
        return {row.student_id: row for row in self.students}

    def summary(self) -> dict:
        valid_students = self.valid_students()
        return {
            "students_total": len(self.students),
            "students_valid": len(valid_students),
            "students_invalid": len([r for r in self.students if r.errors]),
            "students_existing": len([r for r in self.students if r.existing_profile]),
            "will_create": len([r for r in valid_students if r.outcome == "create"]),
            "will_update": len([r for r in valid_students if r.outcome == "update"]),
            "will_skip": len([r for r in valid_students if r.outcome == "skip"]),
            "passed_total": len(self.passed_rows),
            "passed_valid": len([r for r in self.passed_rows if r.is_valid]),
            "passed_invalid": len([r for r in self.passed_rows if r.errors]),
            "enrollments_total": len(self.enrollment_rows),
            "enrollments_valid": len([r for r in self.enrollment_rows if r.is_valid]),
            "enrollments_invalid": len([r for r in self.enrollment_rows if r.errors]),
            "duplicate_rows": self.duplicate_rows,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def to_report(self) -> dict:
        return {
            "file_hash": self.workbook_hash,
            "mode": self.mode,
            "summary": self.summary(),
            "students": [row.to_report() for row in self.students],
            "passed_courses": [row.to_report() for row in self.passed_rows],
            "enrollments": [row.to_report() for row in self.enrollment_rows],
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def _parse_students(reference: Reference, mapping: SheetMapping, mode: str) -> list[StudentRow]:
    rows: list[StudentRow] = []
    seen_numbers: dict[str, int] = {}
    seen_emails: dict[str, int] = {}
    sheet = mapping.sheet.name
    for row_number, values in mapping.sheet.rows:
        row = StudentRow(row=row_number)
        row.student_id = _digits(_cell(mapping, values, "student_id"))
        row.first_name = _text(_cell(mapping, values, "first_name"))
        row.last_name = _text(_cell(mapping, values, "last_name"))
        row.email = _text(_cell(mapping, values, "email")).lower()
        department_raw = _text(_cell(mapping, values, "department"))
        degree_raw = _text(_cell(mapping, values, "degree"))
        entry_year_raw = _digits(_cell(mapping, values, "entry_year"))
        current_term_raw = _digits(_cell(mapping, values, "current_term"))
        gpa_raw = _cell(mapping, values, "gpa")

        def fail(
            field_name: str,
            code: str,
            message: str,
            row: StudentRow = row,
            row_number: int = row_number,
        ) -> None:
            row.errors.append(Issue(sheet, row_number, field_name, code, message))

        if not row.student_id:
            fail("student_id", "REQUIRED", "کد دانشجویی الزامی است.")
        elif not row.student_id.isdigit() or len(row.student_id) > 16:
            fail("student_id", "INVALID_FORMAT", "کد دانشجویی باید فقط رقم باشد (حداکثر ۱۶ رقم).")
        elif row.student_id in seen_numbers:
            fail(
                "student_id",
                "DUPLICATE_IN_FILE",
                f"کد دانشجویی در سطر {seen_numbers[row.student_id]} همین فایل تکرار شده است.",
            )
        if not row.first_name:
            fail("first_name", "REQUIRED", "نام الزامی است.")
        if not row.last_name:
            fail("last_name", "REQUIRED", "نام خانوادگی الزامی است.")
        if not row.email:
            fail("email", "REQUIRED", "ایمیل الزامی است.")
        elif "@" not in row.email or row.email.startswith("@") or row.email.endswith("@"):
            fail("email", "INVALID_EMAIL", "ایمیل معتبر نیست.")
        elif row.email in seen_emails:
            fail(
                "email",
                "DUPLICATE_IN_FILE",
                f"ایمیل در سطر {seen_emails[row.email]} همین فایل تکرار شده است.",
            )
        row.department = _match_department(reference, department_raw)
        if not department_raw:
            fail("department", "REQUIRED", "گروه آموزشی الزامی است.")
        elif row.department is None:
            fail(
                "department",
                "INVALID_DEPARTMENT",
                f"گروه آموزشی «{department_raw}» در سامانه یافت نشد.",
            )
        row.degree = _match_degree(degree_raw) or ""
        if not degree_raw:
            fail("degree", "REQUIRED", "مقطع تحصیلی الزامی است.")
        elif not row.degree:
            fail(
                "degree",
                "INVALID_DEGREE",
                f"مقطع «{degree_raw}» معتبر نیست؛ کارشناسی، ارشد یا دکتری بنویسید.",
            )
        row.entry_year = entry_year_raw
        if not entry_year_raw:
            fail("entry_year", "REQUIRED", "سال ورود الزامی است.")
        elif not (
            entry_year_raw.isdigit()
            and len(entry_year_raw) == 4
            and 1350 <= int(entry_year_raw) <= 1420
        ):
            fail(
                "entry_year",
                "INVALID_ENTRY_YEAR",
                "سال ورود باید عددی چهاررقمی بین ۱۳۵۰ و ۱۴۲۰ باشد.",
            )
        if current_term_raw:
            if current_term_raw.isdigit() and 1 <= int(current_term_raw) <= 20:
                row.current_term = int(current_term_raw)
            else:
                fail(
                    "current_term",
                    "INVALID_CURRENT_TERM",
                    "شمارهٔ ترم جاری باید عددی بین ۱ تا ۲۰ باشد.",
                )
        if _text(gpa_raw):
            grade_value = _decimal(gpa_raw)
            if grade_value is None or grade_value < 0 or grade_value > 20:
                fail("gpa", "INVALID_GPA", "معدل باید عددی بین ۰ تا ۲۰ باشد.")
            else:
                row.gpa = grade_value.quantize(Decimal("0.01"))

        # Existing-account detection on the real unique identifiers.
        if row.email:
            row.existing_user = reference.users_by_email.get(row.email)
        if row.student_id:
            row.existing_profile = reference.profiles_by_number.get(row.student_id)

        if row.existing_profile is not None and row.existing_user is not None:
            if row.existing_profile.user_id != row.existing_user.pk:
                fail(
                    "student_id",
                    "CONFLICT_IDENTITY",
                    "کد دانشجویی و ایمیل به دو حساب متفاوت تعلق دارند؛ این سطر قابل واردکردن نیست.",
                )
        elif row.existing_profile is not None and row.existing_user is None:
            # Student number already belongs to another account: never merge.
            other = row.existing_profile.user
            fail(
                "student_id",
                "DUPLICATE_STUDENT_NUMBER",
                f"کد دانشجویی متعلق به {_mask_email(other.email)} است؛ ایمیل سطر هم‌خوان نیست.",
            )
        elif row.existing_user is not None and row.existing_profile is None:
            if row.existing_user.role != Role.STUDENT:
                fail(
                    "email",
                    "EMAIL_NOT_STUDENT",
                    "این ایمیل متعلق به حساب غیردانشجویی است و در بارگذاری گروهی استفاده نمی‌شود.",
                )
            elif mode == MODE_CREATE_ONLY:
                # An existing account: default behaviour is a safe skip.
                row.outcome = "skip"
                row.warnings.append(
                    Issue(
                        sheet,
                        row_number,
                        "email",
                        "EXISTING_ACCOUNT",
                        "این حساب موجود است؛ برای تکمیل پروفایل، حالت به‌روزرسانی را فعال کنید.",
                    )
                )
            else:
                row.outcome = "update"
                row.changes = _profile_changes(row)

        if row.existing_profile is not None:
            if mode == MODE_CREATE_ONLY:
                row.outcome = "skip"
                row.warnings.append(
                    Issue(
                        sheet,
                        row_number,
                        "student_id",
                        "EXISTING_STUDENT",
                        "این دانشجو موجود است؛ برای به‌روزرسانی، حالت به‌روزرسانی را فعال کنید.",
                    )
                )
            else:
                row.outcome = "update"
                row.changes = _profile_changes(row)
                if not row.changes:
                    row.outcome = "skip"
                    row.warnings.append(
                        Issue(
                            sheet,
                            row_number,
                            "student_id",
                            "NO_CHANGES",
                            "اطلاعات این دانشجو تغییری ندارد.",
                        )
                    )

        if row.errors:
            row.outcome = "error"
        if row.student_id and row.student_id not in seen_numbers:
            seen_numbers[row.student_id] = row_number
        if row.email and row.email not in seen_emails:
            seen_emails[row.email] = row_number
        rows.append(row)
    return rows


def _profile_changes(row: StudentRow) -> list[dict]:
    """Human-readable diff for update mode (shown before confirmation)."""
    changes: list[dict] = []
    user = row.existing_user or (row.existing_profile.user if row.existing_profile else None)
    profile = row.existing_profile
    if user is None:
        return changes
    if row.first_name and row.first_name != user.first_name:
        changes.append(
            {
                "field": "first_name",
                "label": "نام",
                "from": user.first_name,
                "to": row.first_name,
            }
        )
    if row.last_name and row.last_name != user.last_name:
        changes.append(
            {
                "field": "last_name",
                "label": "نام خانوادگی",
                "from": user.last_name,
                "to": row.last_name,
            }
        )
    if profile is None:
        changes.append(
            {
                "field": "profile",
                "label": "پروفایل دانشجویی",
                "from": "—",
                "to": "ساخت پروفایل",
            }
        )
        return changes
    if row.department and row.department.pk != profile.department_id:
        changes.append(
            {
                "field": "department",
                "label": "گروه آموزشی",
                "from": profile.department.name if profile.department else "",
                "to": row.department.name,
            }
        )
    if row.degree and row.degree != profile.degree_level:
        changes.append(
            {
                "field": "degree_level",
                "label": "مقطع",
                "from": profile.get_degree_level_display() if profile.degree_level else "",
                "to": dict(DegreeLevel.choices).get(row.degree, row.degree),
            }
        )
    if row.entry_year and row.entry_year != profile.entry_year:
        changes.append(
            {
                "field": "entry_year",
                "label": "سال ورود",
                "from": profile.entry_year,
                "to": row.entry_year,
            }
        )
    if row.current_term is not None and row.current_term != profile.current_term_number:
        changes.append(
            {
                "field": "current_term_number",
                "label": "شماره ترم جاری",
                "from": profile.current_term_number,
                "to": row.current_term,
            }
        )
    if row.gpa is not None and (profile.current_gpa is None or row.gpa != profile.current_gpa):
        changes.append(
            {
                "field": "current_gpa",
                "label": "معدل",
                "from": str(profile.current_gpa) if profile.current_gpa is not None else "",
                "to": str(row.gpa),
            }
        )
    if not profile.student_number:
        changes.append(
            {
                "field": "student_number",
                "label": "کد دانشجویی",
                "from": "",
                "to": row.student_id,
            }
        )
    return changes


def _parse_history_rows(
    reference: Reference,
    mapping: SheetMapping,
    kind: str,
    students_by_number: dict[str, StudentRow],
    passed_existing: dict[str, set[str]],
    current_existing: dict[str, set[str]],
) -> list[HistoryRow]:
    rows: list[HistoryRow] = []
    seen: dict[tuple[str, str], int] = {}
    sheet = mapping.sheet.name
    for row_number, values in mapping.sheet.rows:
        row = HistoryRow(row=row_number, kind=kind)
        row.student_id = _digits(_cell(mapping, values, "student_id"))
        course_raw = _text(_cell(mapping, values, "course_code"))
        term_raw = _text(_cell(mapping, values, "term"))
        group_raw = _digits(_cell(mapping, values, "group_code")) if kind == "enrollment" else ""

        def fail(
            field_name: str,
            code: str,
            message: str,
            row: HistoryRow = row,
            row_number: int = row_number,
        ) -> None:
            row.errors.append(Issue(sheet, row_number, field_name, code, message))

        if not row.student_id:
            fail("student_id", "REQUIRED", "کد دانشجویی الزامی است.")
        else:
            student = students_by_number.get(row.student_id)
            if student is None:
                fail(
                    "student_id",
                    "UNKNOWN_STUDENT",
                    "این کد دانشجویی در برگهٔ دانشجویان همین فایل نیست.",
                )
            elif student.errors:
                fail(
                    "student_id",
                    "STUDENT_INVALID",
                    "سطر دانشجوی مرتبط دارای خطاست؛ این سطر وارد نمی‌شود.",
                )
            elif student.outcome == "skip":
                fail(
                    "student_id",
                    "STUDENT_SKIPPED",
                    "دانشجو در حالت فعلی نادیده گرفته می‌شود؛ حالت به‌روزرسانی را انتخاب کنید.",
                )
        if not course_raw:
            fail("course_code", "REQUIRED", "کد درس الزامی است.")
        else:
            row.course = _match_course(reference, course_raw)
            if row.course is None:
                fail(
                    "course_code",
                    "UNKNOWN_COURSE",
                    f"درس با کد «{course_raw}» در سرفصل دروس فعال نیست.",
                )
        if not term_raw:
            fail("term", "REQUIRED", "ترم الزامی است.")
        else:
            row.term = _match_term(reference, term_raw)
            if row.term is None:
                fail(
                    "term",
                    "INVALID_TERM",
                    f"ترم «{term_raw}» یافت نشد؛ نام کامل ترم را وارد کنید.",
                )
        if kind == "enrollment":
            row.group_code = group_raw
            if not group_raw:
                fail("group_code", "REQUIRED", "شماره گروه الزامی است.")
            if row.term is not None and row.term.is_current is False and not row.term.is_past:
                row.warnings.append(
                    Issue(
                        sheet,
                        row_number,
                        "term",
                        "FUTURE_TERM",
                        "ترم انتخابی در آینده است؛ صحت آن را بررسی کنید.",
                    )
                )
        else:
            grade_value = _decimal(_cell(mapping, values, "grade"))
            if _text(_cell(mapping, values, "grade")) == "":
                fail("grade", "REQUIRED", "نمره الزامی است.")
            elif grade_value is None or grade_value < 0 or grade_value > 20:
                fail("grade", "INVALID_GRADE", "نمره باید عددی بین ۰ تا ۲۰ باشد.")
            else:
                row.grade = grade_value.quantize(Decimal("0.01"))
                if grade_value < 10:
                    row.warnings.append(
                        Issue(
                            sheet,
                            row_number,
                            "grade",
                            "LOW_GRADE",
                            "نمره کمتر از ۱۰ است؛ رکورد به‌عنوان پاس‌شده ثبت می‌شود.",
                        )
                    )
            if row.term is not None and row.term.is_current:
                fail(
                    "term",
                    "PASSED_IN_CURRENT_TERM",
                    "درس پاس‌شده نمی‌تواند به ترم جاری تعلق داشته باشد.",
                )

        if row.course is not None and row.term is not None:
            key = (row.student_id, normalize_persian(row.course.code))
            if key in seen:
                row.errors.append(
                    Issue(
                        sheet,
                        row_number,
                        "course_code",
                        "DUPLICATE_IN_FILE",
                        f"این درس برای همین دانشجو در سطر {seen[key]} تکرار شده است.",
                    )
                )
            else:
                seen[key] = row_number
            if kind == "enrollment":
                row.offering = _match_offering(reference, row.course, row.term, row.group_code)
                if row.offering is None:
                    if row.term.is_current:
                        fail(
                            "group_code",
                            "UNKNOWN_OFFERING",
                            f"ارائهٔ گروه «{row.group_code}» برای این درس در ترم جاری وجود ندارد.",
                        )
                    else:
                        fail(
                            "group_code",
                            "UNKNOWN_OFFERING",
                            "ارائهٔ این درس در ترم انتخابی یافت نشد.",
                        )
                elif row.offering.term_id != row.term.pk:  # defensive: same query key
                    fail("term", "TERM_MISMATCH", "ترم با ترم ارائهٔ انتخاب‌شده یکسان نیست.")
            else:
                row.offering = _match_offering(reference, row.course, row.term, "")
                if row.offering is None and not row.term.is_past and not row.term.is_current:
                    row.warnings.append(
                        Issue(sheet, row_number, "term", "FUTURE_TERM", "ترم انتخابی در آینده است.")
                    )
                if row.offering is None and row.term.is_past:
                    row.warnings.append(
                        Issue(
                            sheet,
                            row_number,
                            "term",
                            "HISTORICAL_OFFERING_AUTO",
                            "ارائهٔ تاریخی ثبت نشده است؛ یک ارائهٔ بستهٔ تاریخی ایجاد می‌شود.",
                        )
                    )
        rows.append(row)

    # Cross-sheet business rules: a course cannot be both passed and current
    # for the same student, and can never be re-taken after passing.
    for row in rows:
        if row.errors or row.course is None:
            continue
        normalized = normalize_persian(row.course.code)
        if kind == "enrollment":
            if normalized in passed_existing.get(row.student_id, set()):
                row.errors.append(
                    Issue(
                        sheet,
                        row.row,
                        "course_code",
                        "CONFLICT_PASSED_CURRENT",
                        "این درس قبلاً برای دانشجو پاس شده است و نمی‌تواند هم‌زمان اخذ شود.",
                    )
                )
        else:
            if normalized in current_existing.get(row.student_id, set()):
                row.errors.append(
                    Issue(
                        sheet,
                        row.row,
                        "course_code",
                        "CONFLICT_PASSED_CURRENT",
                        "این درس در ترم جاری برای دانشجو فعال است و نمی‌تواند پاس‌شده ثبت شود.",
                    )
                )
    return rows


def _collect_issues(plan_rows: list) -> tuple[list[Issue], list[Issue]]:
    errors: list[Issue] = []
    warnings: list[Issue] = []
    for row in plan_rows:
        errors.extend(row.errors)
        warnings.extend(row.warnings)
    return errors, warnings


def build_plan(
    parsed: ParsedWorkbook,
    raw_mapping: Any,
    mode: str,
) -> ImportPlan:
    """Validate everything and return the preview plan (nothing is written)."""
    if mode not in MODES:
        raise ApiError(VALIDATION_ERROR, "حالت واردکردن نامعتبر است.", http_status=400)
    mappings = resolve_mapping(parsed, raw_mapping)
    reference = load_reference()
    _populate_existing_students(reference, mappings[ROLE_STUDENTS])

    student_rows = _parse_students(reference, mappings[ROLE_STUDENTS], mode)
    students_by_number = {row.student_id: row for row in student_rows if row.student_id}

    # Existing history for the students the file actually touches.
    passed_existing: dict[str, set[str]] = {}
    current_existing: dict[str, set[str]] = {}
    student_numbers = [
        number for number in students_by_number if students_by_number[number].is_valid
    ]
    enrollments = (
        Enrollment.objects.filter(student__student_number__in=student_numbers)
        .select_related("course_offering__course", "course_offering__term")
    )
    for enrollment in enrollments:
        number = enrollment.student.student_number
        code = normalize_persian(enrollment.course_offering.course.code)
        if enrollment.status == EnrollmentStatus.PASSED:
            passed_existing.setdefault(number, set()).add(code)
        if enrollment.status in (EnrollmentStatus.PLANNED, EnrollmentStatus.ENROLLED):
            current_existing.setdefault(number, set()).add(code)

    passed_rows: list[HistoryRow] = []
    enrollment_rows: list[HistoryRow] = []
    if ROLE_PASSED in mappings:
        passed_rows = _parse_history_rows(
            reference,
            mappings[ROLE_PASSED],
            "passed",
            students_by_number,
            passed_existing,
            current_existing,
        )
    if ROLE_ENROLLMENTS in mappings:
        enrollment_rows = _parse_history_rows(
            reference,
            mappings[ROLE_ENROLLMENTS],
            "enrollment",
            students_by_number,
            passed_existing,
            current_existing,
        )

    # Same-file conflict: a course passed in one sheet and taken in the other.
    passed_by_student: dict[str, set[str]] = {}
    for row in passed_rows:
        if row.course is not None and not row.errors:
            passed_by_student.setdefault(row.student_id, set()).add(
                normalize_persian(row.course.code)
            )
    for row in enrollment_rows:
        if row.errors or row.course is None:
            continue
        if normalize_persian(row.course.code) in passed_by_student.get(row.student_id, set()):
            row.errors.append(
                Issue(
                    mappings[ROLE_ENROLLMENTS].sheet.name,
                    row.row,
                    "course_code",
                    "CONFLICT_PASSED_CURRENT",
                    "این درس در دروس پاس‌شدهٔ همین فایل هم هست؛ اخذ هم‌زمان مجاز نیست.",
                )
            )

    errors, warnings = _collect_issues(student_rows)
    history_errors, history_warnings = _collect_issues(passed_rows + enrollment_rows)
    errors.extend(history_errors)
    warnings.extend(history_warnings)
    duplicates = len([issue for issue in errors if issue.code == "DUPLICATE_IN_FILE"])

    return ImportPlan(
        workbook_hash=parsed.hash,
        mode=mode,
        students=student_rows,
        passed_rows=passed_rows,
        enrollment_rows=enrollment_rows,
        errors=errors,
        warnings=warnings,
        duplicate_rows=duplicates,
    )


# ── Execution ─────────────────────────────────────────────────────────────


def _apply_profile_changes(user: User, profile: StudentProfile, row: StudentRow) -> None:
    """Update mode only: apply the exact diff shown in the preview."""
    user_fields: list[str] = []
    if row.first_name and row.first_name != user.first_name:
        user.first_name = row.first_name
        user_fields.append("first_name")
    if row.last_name and row.last_name != user.last_name:
        user.last_name = row.last_name
        user_fields.append("last_name")
    if user_fields:
        user.save(update_fields=[*user_fields, "updated_at"])

    profile_fields: list[str] = []
    if row.department and row.department.pk != profile.department_id:
        profile.department = row.department
        profile.faculty = row.department.faculty
        profile_fields.extend(["department", "faculty"])
    if row.degree and row.degree != profile.degree_level:
        profile.degree_level = row.degree
        profile_fields.append("degree_level")
    if row.entry_year and row.entry_year != profile.entry_year:
        profile.entry_year = row.entry_year
        profile_fields.append("entry_year")
    if row.current_term is not None and row.current_term != profile.current_term_number:
        profile.current_term_number = row.current_term
        profile_fields.append("current_term_number")
    if row.gpa is not None and row.gpa != profile.current_gpa:
        profile.current_gpa = row.gpa
        profile_fields.append("current_gpa")
    if not profile.student_number and row.student_id:
        profile.student_number = row.student_id
        profile_fields.append("student_number")
    if profile_fields:
        profile.save(update_fields=[*profile_fields, "updated_at"])


def _ensure_offering(
    course: Course, term: AcademicTerm, group_code: str
) -> CourseOffering:
    """Find or additively create the historical offering row.

    Mirrors the existing academic-history convention (closed section, capacity
    0) when the registrar data predates the catalogue's offering rows.
    """
    candidates = CourseOffering.objects.filter(course=course, term=term)
    if group_code:
        found = candidates.filter(section_code=group_code).first()
        if found is not None:
            return found
    else:
        found = candidates.order_by("section_code").first()
        if found is not None:
            return found
    return CourseOffering.objects.create(
        course=course,
        term=term,
        section_code=group_code or "01",
        capacity=0,
        status=OfferingStatus.CLOSED,
    )


def _import_student(
    plan: ImportPlan, row: StudentRow, password_out: list[tuple[str, str]]
) -> dict:
    """One student = one transaction (profile + history never half-imported)."""
    passed_rows = [
        item for item in plan.passed_rows if item.student_id == row.student_id and not item.errors
    ]
    enrollment_rows = [
        item
        for item in plan.enrollment_rows
        if item.student_id == row.student_id and not item.errors
    ]
    passed_imported = 0
    enrollment_imported = 0
    warnings: list[str] = []

    with transaction.atomic():
        if row.existing_profile is not None:
            profile = row.existing_profile
            user = profile.user
            if plan.mode == MODE_UPSERT:
                _apply_profile_changes(user, profile, row)
        elif row.existing_user is not None and row.existing_user.role == Role.STUDENT:
            # Update mode: an account exists without a profile yet.
            user = row.existing_user
            profile, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "student_number": row.student_id,
                    "department": row.department,
                    "faculty": row.department.faculty if row.department else None,
                    "degree_level": row.degree,
                    "entry_year": row.entry_year,
                    "current_term_number": row.current_term,
                    "current_gpa": row.gpa,
                },
            )
            _apply_profile_changes(user, profile, row)
        else:
            password = _generate_password()
            user = User.objects.create_user(
                email=row.email,
                password=password,
                first_name=row.first_name,
                last_name=row.last_name,
                role=Role.STUDENT,
            )
            profile = StudentProfile.objects.create(
                user=user,
                student_number=row.student_id,
                department=row.department,
                faculty=row.department.faculty if row.department else None,
                degree_level=row.degree,
                entry_year=row.entry_year,
                current_term_number=row.current_term,
                current_gpa=row.gpa,
            )
            password_out.append((row.email, password))

        for item in passed_rows:
            if item.course is None or item.term is None:
                continue
            offering = _ensure_offering(item.course, item.term, item.group_code)
            existing = Enrollment.objects.filter(student=profile, course_offering=offering).first()
            if existing is None:
                Enrollment.objects.create(
                    student=profile,
                    course_offering=offering,
                    status=EnrollmentStatus.PASSED,
                    grade=item.grade,
                )
                passed_imported += 1
            elif existing.status == EnrollmentStatus.PASSED and existing.grade is None:
                # Same record: fill the grade the registrar export provides.
                existing.grade = item.grade
                existing.save(update_fields=["grade", "updated_at"])
                passed_imported += 1
            else:
                warnings.append(
                    f"درس {item.course.code} در {item.term.name} از قبل ثبت شده بود."
                )

        for item in enrollment_rows:
            if item.course is None or item.term is None or item.offering is None:
                continue
            existing = Enrollment.objects.filter(
                student=profile, course_offering=item.offering
            ).first()
            if existing is None:
                Enrollment.objects.create(
                    student=profile,
                    course_offering=item.offering,
                    status=EnrollmentStatus.ENROLLED,
                )
                enrollment_imported += 1
            elif existing.status == EnrollmentStatus.PLANNED:
                existing.status = EnrollmentStatus.ENROLLED
                existing.save(update_fields=["status", "updated_at"])
                enrollment_imported += 1
                warnings.append(f"درس {item.course.code} از برنامه به ثبت‌نام تبدیل شد.")
            else:
                warnings.append(
                    f"درس {item.course.code} در {item.offering.term.name} از قبل ثبت شده بود."
                )

    return {
        "row": row.row,
        "student_id": row.student_id,
        "email": row.email,
        "full_name": f"{row.first_name} {row.last_name}".strip(),
        "outcome": row.outcome if row.outcome != "create" else "created",
        "passed_imported": passed_imported,
        "enrollments_imported": enrollment_imported,
        "warnings": warnings,
    }


def execute_plan(plan: ImportPlan, actor) -> dict:
    """Execute a previously validated plan; per-student transactions."""
    valid = plan.valid_students()
    if not valid:
        raise ApiError(
            VALIDATION_ERROR,
            "هیچ سطر دانشجوی معتبری برای واردکردن وجود ندارد.",
            http_status=400,
        )

    results: list[dict] = []
    created_passwords: list[tuple[str, str]] = []
    counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    passed_imported = 0
    enrollment_imported = 0
    # Failures that validation could not predict; row-level validation issues
    # already live in ``plan.errors`` and must not be counted twice.
    extra_errors: list[dict] = []

    for row in plan.students:
        if not row.is_valid:
            results.append(
                {
                    "row": row.row,
                    "student_id": row.student_id,
                    "email": row.email,
                    "full_name": f"{row.first_name} {row.last_name}".strip(),
                    "outcome": "failed",
                    "errors": [issue.to_dict() for issue in row.errors],
                }
            )
            counts["failed"] += 1
            continue
        if row.outcome == "skip":
            results.append(
                {
                    "row": row.row,
                    "student_id": row.student_id,
                    "email": row.email,
                    "full_name": f"{row.first_name} {row.last_name}".strip(),
                    "outcome": "skipped",
                    "warnings": [issue.message for issue in row.warnings],
                }
            )
            counts["skipped"] += 1
            continue
        try:
            result = _import_student(plan, row, created_passwords)
        except Exception as exc:  # noqa: BLE001 - one student must not sink the batch
            logger.exception("student_import_failed", extra={"student": row.student_id})
            issue = {
                "sheet": "",
                "row": row.row,
                "field": "",
                "code": "IMPORT_FAILED",
                "message": f"ثبت این دانشجو با خطا مواجه شد: {type(exc).__name__}",
            }
            extra_errors.append(issue)
            results.append(
                {
                    "row": row.row,
                    "student_id": row.student_id,
                    "email": row.email,
                    "full_name": f"{row.first_name} {row.last_name}".strip(),
                    "outcome": "failed",
                    "errors": [issue],
                }
            )
            counts["failed"] += 1
            continue
        if result["outcome"] == "created":
            counts["created"] += 1
        else:
            counts["updated"] += 1
        passed_imported += result["passed_imported"]
        enrollment_imported += result["enrollments_imported"]
        results.append(result)

    summary = {
        "students_processed": len(plan.students),
        "created": counts["created"],
        "updated": counts["updated"],
        "skipped": counts["skipped"],
        "failed": counts["failed"],
        "passed_imported": passed_imported,
        "enrollments_imported": enrollment_imported,
        "errors": len(plan.errors) + len(extra_errors),
        "warnings": len(plan.warnings),
    }

    audit = AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=AuditAction.CREATE,
        entity_type="student_import",
        entity_id=plan.workbook_hash[:16],
        metadata={
            "file_hash": plan.workbook_hash,
            "mode": plan.mode,
            "summary": summary,
            "students": [
                {
                    "student_id": result.get("student_id", ""),
                    "email": _mask_email(result.get("email", "")),
                    "outcome": result["outcome"],
                }
                for result in results
            ],
        },
    )

    return {
        "file_hash": plan.workbook_hash,
        "mode": plan.mode,
        "summary": summary,
        "results": results,
        "errors": [issue.to_dict() for issue in plan.errors] + extra_errors,
        "created_credentials": [
            {"email": email, "password": password} for email, password in created_passwords
        ],
        "audit_id": audit.pk,
    }
