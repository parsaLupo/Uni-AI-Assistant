"""Jalali (Shamsi) -> Gregorian date conversion.

Used by the `seed` command to place the real exam dates found in
`data/course-offering*.json` (format «امتحان(1405.10.20) ساعت : 16:00-18:00»)
onto the Gregorian timeline the database stores (OA-14: API/DB stay UTC
Gregorian; Jalali is presentation).

Algorithm: the well-known arithmetic conversion by Behrang Noruzi Niya
(public domain — no dependency added, AGENTS.md rule 10).
Valid for Jalali years 1178-3178; the university data sits far inside that.
"""

from __future__ import annotations

from datetime import date


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """Convert a Jalali (year, month, day) triple to Gregorian (y, m, d)."""
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1

    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    months = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    for i in range(1, 13):
        if gd <= months[i]:
            gm = i
            break
        gd -= months[i]
    return gy, gm, gd


def jalali_date(jy: int, jm: int, jd: int) -> date:
    """Convenience wrapper returning a `datetime.date`."""
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    return date(gy, gm, gd)

