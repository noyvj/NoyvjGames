"""The shared seasonal-events date engine."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import seasonal_events as se  # noqa: E402


def _ids(today):
    return [e["id"] for e in se.active_events(today)]


def test_easter_sunday_known_years():
    assert se.easter_sunday(2026) == date(2026, 4, 5)
    assert se.easter_sunday(2027) == date(2027, 3, 28)
    assert se.easter_sunday(2028) == date(2028, 4, 16)
    assert se.easter_sunday(2024) == date(2024, 3, 31)


def test_nth_weekday_thanksgiving_and_last_monday():
    assert se.nth_weekday(2026, 11, 3, 4) == date(2026, 11, 26)
    assert se.nth_weekday(2027, 11, 3, 4) == date(2027, 11, 25)
    assert se.nth_weekday(2026, 5, 0, -1) == date(2026, 5, 25)
    assert se.nth_weekday(2026, 12, 3, -1) == date(2026, 12, 31)


def test_fixed_windows_with_before_and_after():
    assert "halloween" in _ids(date(2026, 10, 25))
    assert "halloween" in _ids(date(2026, 10, 31))
    assert "halloween" in _ids(date(2026, 11, 1))
    assert "halloween" not in _ids(date(2026, 10, 24))
    assert "halloween" not in _ids(date(2026, 11, 2))


def test_windows_that_straddle_the_new_year_work_from_both_sides():
    assert "new_year" in _ids(date(2026, 12, 30))
    assert "new_year" in _ids(date(2027, 1, 3))
    assert "new_year" not in _ids(date(2027, 1, 5))
    assert "christmas" in _ids(date(2026, 12, 18)) and "christmas" not in _ids(date(2026, 12, 17))
    assert "christmas" in _ids(date(2026, 12, 26)) and "christmas" not in _ids(date(2026, 12, 27))


def test_easter_and_thanksgiving_follow_their_moving_dates():
    assert "easter" in _ids(date(2026, 4, 2)) and "easter" in _ids(date(2026, 4, 6))
    assert "easter" not in _ids(date(2026, 4, 8))
    assert "thanksgiving" in _ids(date(2026, 11, 23)) and "thanksgiving" in _ids(date(2026, 11, 27))
    assert "thanksgiving" not in _ids(date(2026, 11, 30))


def test_table_events_use_the_read_dates_and_skip_unknown_years():
    assert "hanukkah" in _ids(date(2026, 12, 4)) and "hanukkah" in _ids(date(2026, 12, 12))
    assert "hanukkah" not in _ids(date(2026, 12, 13))
    assert "hanukkah" in _ids(date(2028, 1, 1))  # the 2027 range runs past new year
    assert "lunar_new_year" in _ids(date(2026, 2, 17))
    assert "diwali" in _ids(date(2026, 11, 8))
    assert "diwali" not in _ids(date(2031, 11, 1))  # the table does not reach 2031
    assert "hanukkah" not in _ids(date(2031, 12, 10))


def test_most_days_have_no_event():
    quiet = [d for d in (date(2026, 3, 1), date(2026, 5, 20), date(2026, 8, 15), date(2026, 9, 20)) if _ids(d)]
    assert quiet == []


def test_bad_rules_never_raise():
    for bad in ({}, {"when": None}, {"when": {"kind": "nope"}}, {"when": {"kind": "fixed", "month": 13, "day": 40}},
                {"when": {"kind": "table", "table": "missing"}}):
        assert se.event_window(dict(bad, id="x"), 2026) is None
    assert se.active_events(date(2026, 10, 31), events=[{"id": "x", "when": {"kind": "fixed", "month": 2, "day": 30}}]) == []


def test_badge_ids_name_the_holidays_own_year():
    events = {e["id"]: e for e in se.active_events(date(2026, 10, 31))}
    assert se.badge_id(events["halloween"]) == "halloween-2026"
    ny = se.active_events(date(2027, 1, 2), events=[e for e in se.DEFAULT_EVENTS if e["id"] == "new_year"])[0]
    assert se.badge_id(ny) == "new_year-2027"
    ny_eve = se.active_events(date(2026, 12, 31), events=[e for e in se.DEFAULT_EVENTS if e["id"] == "new_year"])[0]
    assert se.badge_id(ny_eve) == "new_year-2027"


def test_dates_file_is_sourced_and_parses():
    data = se.load_dates()
    assert data["read"] == "2026-09-27"
    for key in ("hanukkah", "lunar_new_year", "diwali"):
        assert data[key]["source"].startswith("https://en.wikipedia.org/")
        assert data[key]["years"]


def test_load_dates_accepts_fetched_text_and_bad_text():
    assert se.load_dates("not json") == {}
    assert se.event_window({"id": "d", "when": {"kind": "table", "table": "diwali"}}, 2026) is None  # empty tables
    se.load_dates('{"diwali": {"years": {"2030": "2030-11-01"}}}')
    assert se.event_window({"id": "d", "when": {"kind": "table", "table": "diwali"}}, 2030) == (date(2030, 11, 1), date(2030, 11, 1))
    se._dates_cache = None
    assert se.load_dates()["read"] == "2026-09-27"
