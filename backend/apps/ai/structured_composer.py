"""Deterministic answer composition from structured PostgreSQL facts.

Why this exists: for questions that the router sends to STRUCTURED mode, the
database facts produced by ``StructuredQueryService`` fully determine the
answer — sending them to a chat LLM adds a point of failure (model refusals,
timeouts, provider 413s) without adding information. The grounded Persian
phrases below are therefore assembled directly from the fact dicts, and
``AnswerService`` only falls back to the LLM when a fact type or a required
field is not covered here. Composition can never invent data: every string a
template emits comes from a database record in the fact.
"""

from __future__ import annotations

from typing import Any

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(value: Any) -> str:
    """Render a fact value for display with Persian digits."""
    return str(value).translate(_PERSIAN_DIGITS)


def _course_ref(fact: dict[str, Any]) -> tuple[str, str] | None:
    """(display name, code display) from a course-bearing fact."""
    code = fact.get("course_code")
    title = fact.get("course_title")
    if not code or not title:
        return None
    return str(title), _fa(code)


def _format_moment(value: Any) -> str:
    """ISO datetime/date → «YYYY/MM/DD ساعت HH:MM» (Persian digits)."""
    if not value:
        return "?"
    text = str(value)
    date_part, _, time_part = text.partition("T")
    display = _fa(date_part.replace("-", "/")) if date_part else _fa(text)
    if time_part:
        display += f" ساعت {_fa(time_part[:5])}"
    return display


def _compose_prerequisites(fact: dict[str, Any]) -> str | None:
    ref = _course_ref(fact)
    if ref is None:
        return None
    title, code = ref
    prerequisites = fact.get("prerequisites") or []
    if not prerequisites:
        return f"در پایگاه داده پیش‌نیازی برای «{title}» (کد {code}) ثبت نشده است."
    lines = "\n".join(
        f"- «{item.get('title')}» (کد {_fa(item.get('code'))})"
        for item in prerequisites
    )
    return (
        f"پیش‌نیازهای «{title}» (کد {code}) بر اساس رکوردهای پایگاه داده "
        f"عبارت‌اند از:\n{lines}"
    )


def _compose_course_ambiguous(fact: dict[str, Any]) -> str | None:
    matches = fact.get("matches") or []
    if not matches:
        return None
    lines = "\n".join(
        f"- «{match.get('title')}» (کد {_fa(match.get('code'))})"
        for match in matches
    )
    note = str(fact.get("note") or "").strip()
    return f"{note}\n{lines}" if note else lines


def _compose_credits(fact: dict[str, Any]) -> str | None:
    ref = _course_ref(fact)
    credits = fact.get("credits")
    if ref is None or credits is None:
        return None
    title, code = ref
    return f"«{title}» (کد {code}) {_fa(credits)} واحد دارد."


def _compose_exam(fact: dict[str, Any]) -> str | None:
    ref = _course_ref(fact)
    if ref is None:
        return None
    title, code = ref
    starts = _format_moment(fact.get("starts_at"))
    ends = _format_moment(fact.get("ends_at"))
    term = str(fact.get("term") or "").strip()
    head = (
        f"برنامه امتحان «{title}» (کد {code})"
        + (f" در ترم {term}" if term else "")
        + ":"
    )
    lines = [f"- زمان: از {starts} تا {ends}"]
    classroom = str(fact.get("classroom") or "").strip()
    if classroom:
        lines.append(f"- محل: {classroom}")
    return head + "\n" + "\n".join(lines)


def _compose_professor(fact: dict[str, Any]) -> str | None:
    ref = _course_ref(fact)
    professor = str(fact.get("professor") or "").strip()
    if ref is None or not professor:
        return None
    title, code = ref
    term = str(fact.get("term") or "").strip()
    return (
        f"استاد درس «{title}» (کد {code})"
        + (f" در ترم {term}" if term else "")
        + f": {professor}"
    )


def _compose_academic_calendar(fact: dict[str, Any]) -> str | None:
    term_name = str(fact.get("term_name") or "").strip()
    if not term_name:
        return None
    year = str(fact.get("academic_year") or "").strip()
    return (
        f"ترم «{term_name}»"
        + (f" (سال تحصیلی {_fa(year)})" if year else "")
        + f" از {_format_moment(fact.get('starts_at'))} تا "
        f"{_format_moment(fact.get('ends_at'))} است."
    )


def _compose_eligibility(fact: dict[str, Any]) -> str | None:
    ref = _course_ref(fact)
    if ref is None:
        return None
    title, code = ref
    if fact.get("eligible"):
        return (
            f"بله؛ پیش‌نیازهای «{title}» (کد {code}) را گذرانده‌اید و مجاز به "
            f"برداشتن آن هستید."
        )
    missing = fact.get("missing_prerequisites") or []
    if not missing:
        return None
    lines = "\n".join(f"- درس با کد {_fa(item)}" for item in missing)
    return (
        f"برای برداشتن «{title}» (کد {code}) ابتدا باید این پیش‌نیازها را "
        f"گذرانده باشید:\n{lines}"
    )


def _compose_schedule(fact: dict[str, Any]) -> str | None:
    rows = fact.get("schedule")
    if rows is None:
        return None
    if not rows:
        return "برای این درس در پایگاه داده برنامه کلاسی ثبت نشده است."
    lines = []
    for row in rows:
        line = (
            f"- «{row.get('course_title')}» گروه {_fa(row.get('section'))}: "
            f"{row.get('weekday')}، {_fa(row.get('start_time'))} تا "
            f"{_fa(row.get('end_time'))}"
        )
        classroom = str(row.get("classroom") or "").strip()
        if classroom:
            line += f"، {classroom}"
        lines.append(line)
    return "برنامه کلاس‌های ثبت‌شده در پایگاه داده:\n" + "\n".join(lines)


def _compose_calendar(fact: dict[str, Any]) -> str | None:
    events = fact.get("events")
    if events is None:
        return None
    if not events:
        return "رویدادی در تقویم دانشگاه برای ترم جاری ثبت نشده است."
    lines = [
        f"- «{event.get('title')}»: {_format_moment(event.get('starts_at'))}"
        for event in events
    ]
    return "رویدادهای ثبت‌شده در تقویم دانشگاه:\n" + "\n".join(lines)


def _compose_offering(fact: dict[str, Any]) -> str | None:
    code = fact.get("course_code")
    title = fact.get("course_title")
    if not code or not title:
        return None
    term = str(fact.get("term") or "").strip()
    status = str(fact.get("status") or "").strip()
    line = f"«{title}» (کد {_fa(code)}) در پایگاه داده ارائه ثبت‌شده دارد"
    if term:
        line += f" در ترم {term}"
    section = fact.get("section")
    if section:
        line += f" — گروه {_fa(section)}"
    if status:
        line += f" — وضعیت {status}"
    return line + "."


_COMPOSERS = {
    "prerequisites": _compose_prerequisites,
    "course_ambiguous": _compose_course_ambiguous,
    "credits": _compose_credits,
    "exam": _compose_exam,
    "professor": _compose_professor,
    "academic_calendar": _compose_academic_calendar,
    "eligibility": _compose_eligibility,
    "schedule": _compose_schedule,
    "calendar": _compose_calendar,
    "offering": _compose_offering,
}


def compose_structured_answer(facts: list[dict[str, Any]] | None) -> str | None:
    """Compose a grounded Persian answer from structured facts.

    Returns ``None`` when the facts cannot be composed deterministically
    (no facts, an unknown fact type, or a fact missing required fields);
    the caller then falls back to the normal LLM answer path.
    """
    fact_list = facts or []
    if not fact_list:
        return None
    sections: list[str] = []
    for fact in fact_list:
        if not isinstance(fact, dict):
            return None
        composer = _COMPOSERS.get(fact.get("type"))
        if composer is None:
            return None
        try:
            section = composer(fact)
        except Exception:  # noqa: BLE001 — malformed fact; fall back to LLM
            return None
        if section is None:
            return None
        sections.append(section.strip())
    return "\n\n".join(sections)
