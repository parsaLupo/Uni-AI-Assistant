"""Pure parser contract for the seed schedule/exam strings (no DB needed).

The dataset embeds weekly sessions and exam slots as Persian strings whose
weekday names mix Arabic (ي/ك) and Persian (ی/ک) letterforms and use a plain
space OR a ZWNJ between compound names («يك شنبه», «سه‌شنبه»). These tests pin
the parser against every real variant so a future edit cannot re-introduce the
bug that mapped every compound weekday to «شنبه» (Saturday).
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.common.seed_data import TEHRAN_TZ, parse_class_session, parse_exam_slot
from apps.courses.models import Weekday

UTC = ZoneInfo("UTC")


class TestWeekdayParsing:
    def test_joined_and_separated_compound_names(self):
        # «يك شنبه» uses Arabic ي/ك; «یکشنبه» uses Persian letters joined.
        for line in (
            "درس(ت): يك شنبه 08:00-09:00 مكان: كلاس 1",
            "درس(ت): یک شنبه 08:00-09:00 مکان: کلاس 1",
            "درس(ت): یکشنبه 08:00-09:00 مکان: کلاس 1",
        ):
            parsed = parse_class_session(line)
            assert parsed is not None
            assert parsed[0] is Weekday.SUNDAY, line

    def test_tuesday_space_vs_zwnj(self):
        for line in (
            "درس(ت): سه شنبه 13:00-14:00",
            "درس(ت): سه‌شنبه 13:00-14:00",
            "درس(ع): سه‌شنبه 08:00-10:00",
        ):
            parsed = parse_class_session(line)
            assert parsed is not None
            assert parsed[0] is Weekday.TUESDAY, line

    def test_remaining_weekdays(self):
        cases = {
            "درس(ت): شنبه 10:00-12:00": Weekday.SATURDAY,
            "درس(ت): دوشنبه 15:00-17:00": Weekday.MONDAY,
            "درس(ت): چهارشنبه 11:00-12:00": Weekday.WEDNESDAY,
            "درس(ت): چهار شنبه 11:00-12:00": Weekday.WEDNESDAY,
            "درس(ت): پنجشنبه 09:00-11:00": Weekday.THURSDAY,
            "درس(ت): پنج شنبه 09:00-11:00": Weekday.THURSDAY,
            "درس(ت): جمعه 08:00-10:00": Weekday.FRIDAY,
        }
        for line, weekday in cases.items():
            parsed = parse_class_session(line)
            assert parsed is not None
            assert parsed[0] is weekday, line

    def test_compound_names_never_fall_back_to_saturday(self):
        # The original bug: «يك شنبه»/«سه شنبه» matched the bare «شنبه»
        # pattern and every such class became SATURDAY.
        for line in (
            "درس(ت): يك شنبه 10:00-12:00",
            "درس(ت): سه شنبه 10:00-12:00",
            "درس(ت): چهارشنبه 10:00-12:00",
            "درس(ت): پنج شنبه 10:00-12:00",
        ):
            assert parse_class_session(line)[0] is not Weekday.SATURDAY, line


class TestClassSessionParsing:
    def test_time_range_and_room(self):
        parsed = parse_class_session(
            "درس(ت): شنبه 13:00-15:00 مکان: دانشكده برق و كامپيوتر كلاس 114"
        )
        assert parsed == (
            Weekday.SATURDAY,
            time(13, 0),
            time(15, 0),
            "دانشكده برق و كامپيوتر كلاس 114",
        )

    def test_missing_room_is_empty_string(self):
        parsed = parse_class_session("درس(ت): دوشنبه 09:00-10:00")
        assert parsed is not None
        assert parsed[3] == ""

    def test_non_session_lines_return_none(self):
        # Exam lines and continuation-row references must never become
        # weekly sessions.
        assert parse_class_session("امتحان(1405.10.22) ساعت : 10:00-12:00") is None
        assert parse_class_session("") is None
        assert parse_class_session("سرفصل درس: برنامه‌سازی پیشرفته") is None


class TestExamSlotParsing:
    def test_jalali_date_and_times(self):
        # 1405.10.22 (Jalali) → 2027-01-12 (Gregorian).
        parsed = parse_exam_slot("امتحان(1405.10.22) ساعت : 10:00-12:00")
        assert parsed == (date(2027, 1, 12), time(10, 0), time(12, 0), "")

    def test_class_session_is_never_read_as_exam(self):
        assert parse_exam_slot("درس(ت): شنبه 13:00-15:00 مکان: کلاس 114") is None
        assert parse_exam_slot("") is None

    def test_tehran_aware_instant(self):
        # The stored instant must carry the announced Tehran wall-clock time:
        # 10:00 Asia/Tehran (+03:30) == 06:30 UTC — NOT 10:00 UTC.
        parsed = parse_exam_slot("امتحان(1405.10.22) ساعت : 10:00-12:00")
        assert parsed is not None
        exam_date, starts, _, _ = parsed
        instant = timezone.make_aware(datetime.combine(exam_date, starts), TEHRAN_TZ)
        assert instant.astimezone(UTC) == datetime(2027, 1, 12, 6, 30, tzinfo=UTC)
        assert instant.astimezone(TEHRAN_TZ).strftime("%H:%M") == "10:00"
