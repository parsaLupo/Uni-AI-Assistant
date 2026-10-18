"""Jalali conversion tests against authoritative Nowruz anchors."""

from datetime import date

from apps.common.jalali import jalali_date, jalali_to_gregorian


def test_nowruz_1404_is_march_2025():
    assert jalali_to_gregorian(1404, 1, 1) == (2025, 3, 21)


def test_nowruz_1403_is_march_2024():
    assert jalali_to_gregorian(1403, 1, 1) == (2024, 3, 20)


def test_exam_date_from_the_dataset_1405_10_20():
    # The exact date embedded in data/course-offering*.json exam strings.
    result = jalali_date(1405, 10, 20)
    assert isinstance(result, date)
    assert (result.year, result.month, result.day) == (2027, 1, 10)
