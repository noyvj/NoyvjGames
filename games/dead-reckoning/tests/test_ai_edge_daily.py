"""Edge-case tests for daily.py: limits, boundaries, and rejection paths."""

import datetime


import daily


def test_parse_date_handles_empty_and_zero_input():
    """Rejects empty, zero-length, wrong types, and out-of-range strings."""
    assert daily.parse_date("") is None
    assert daily.parse_date(None) is None
    assert daily.parse_date(123) is None
    assert daily.parse_date("short") is None
    assert daily.parse_date("a" * 100) is None


def test_parse_date_accepts_boundary_dates():
    """Accepts exactly EPOCH and LAST_DATE as valid dates."""
    epoch = daily.parse_date(daily.EPOCH)
    last = daily.parse_date(daily.LAST_DATE)
    assert isinstance(epoch, datetime.date) and epoch.isoformat() == daily.EPOCH
    assert isinstance(last, datetime.date) and last.isoformat() == daily.LAST_DATE


def test_playable_respects_epoch_and_today_bounds():
    """Only returns True for real dates between EPOCH and today (inclusive)."""
    assert daily.playable(daily.EPOCH, daily.EPOCH) is True
    assert daily.playable("2026-10-11", "2026-10-11") is True
    assert daily.playable("2026-10-02", "2026-10-01") is False
    assert daily.playable("2025-12-31", "2026-10-01") is False
    assert daily.playable("not-a-date", "2026-10-01") is False


def test_clean_days_truncates_at_max_days_and_keeps_boundaries():
    """Truncates to MAX_DAYS_SAVED and keeps dates exactly at EPOCH/LAST_DATE."""
    raw = {}
    for i in range(4005):
        d = daily.add_days(daily.EPOCH, i)
        raw[d] = {"stars": 1, "best_error_nm": 0.1, "tries": 1}

    cleaned = daily.clean_days(raw)
    assert len(cleaned) == daily.MAX_DAYS_SAVED

    raw2 = {daily.EPOCH: {"stars": 1, "best_error_nm": 0.1, "tries": 1},
            daily.LAST_DATE: {"stars": 1, "best_error_nm": 0.1, "tries": 1}}
    cleaned2 = daily.clean_days(raw2)
    assert daily.EPOCH in cleaned2 and daily.LAST_DATE in cleaned2


def test_merge_record_handles_none_and_clamps_tries():
    """Defaults to new record when old is None, clamps tries to 99999."""
    rec = daily.merge_record(None, 3, 0.5, True)
    assert rec == {"stars": 3, "best_error_nm": 0.5, "tries": 1}

    rec = daily.merge_record({"stars": 1, "best_error_nm": None, "tries": 1}, 5, 0.1, True)
    assert rec["stars"] == 5

    rec = daily.merge_record({"stars": 1, "best_error_nm": None, "tries": 99998}, 1, 0.1, True)
    assert rec["tries"] == 99999


def test_tally_handles_empty_and_past_dates():
    """Returns zero played/three for empty input, ignores dates before EPOCH."""
    tally = daily.tally({}, "2026-10-11")
    assert tally["played"] == 0 and tally["three"] == 0

    tally = daily.tally({"2025-01-01": {"stars": 3, "best_error_nm": 0.1, "tries": 1}}, "2026-10-11")
    assert tally["played"] == 0

    tally = daily.tally({}, "2025-01-01")
    assert tally["open"] == 0
