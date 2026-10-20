"""Edge-case tests for daily.py public functions."""

from datetime import date, timedelta

import daily


def test_parse_date_rejects_invalid_types_and_formats():
    """parse_date returns None for non-strings, wrong lengths, and bad separators."""
    assert daily.parse_date(None) is None
    assert daily.parse_date(1234567890) is None
    assert daily.parse_date("2026/10/01") is None
    assert daily.parse_date("2026-10-01T00:00") is None
    assert daily.parse_date("") is None
    assert daily.parse_date("2026-1-1") is None
    assert daily.parse_date("2026-10-01") is not None


def test_playable_respects_epoch_and_today_boundaries():
    """playable returns True only when both arguments are valid dates and text is between EPOCH and today."""
    epoch = "2026-10-01"
    today = "2026-10-11"
    assert daily.playable(epoch, today) is True
    assert daily.playable(today, today) is True
    assert daily.playable("2026-09-30", today) is False
    assert daily.playable("2026-10-12", today) is False
    assert daily.playable(epoch, "2025-01-01") is False
    assert daily.playable("garbage", today) is False
    assert daily.playable(epoch, "garbage") is False


def test_clean_days_clamps_values_and_respects_max_limit():
    """clean_days clamps tier to 0-3, net to 0-10^6, tries to 1-999, and drops entries past MAX_DAYS_SAVED."""
    raw = {
        "2026-10-01": {"tier": -5, "net": -100, "tries": 0},
        "2026-10-02": {"tier": 10, "net": 9999999, "tries": 2000},
    }
    base = date(2026, 10, 1)
    for i in range(2, 4006):
        d = (base + timedelta(days=i)).isoformat()
        raw[d] = {"tier": 1, "net": 100, "tries": 1}

    result = daily.clean_days(raw)

    assert result["2026-10-01"]["tier"] == 0
    assert result["2026-10-01"]["net"] == 0
    assert result["2026-10-01"]["tries"] == 1
    assert result["2026-10-02"]["tier"] == 3
    assert result["2026-10-02"]["net"] == 1000000
    assert result["2026-10-02"]["tries"] == 999
    assert len(result) == daily.MAX_DAYS_SAVED


def test_tier_of_handles_exact_par_boundary_and_negative_net():
    """tier_of returns 'par' when net equals par, and 'clean' when net is below par, even if negative."""
    outcome_clean = {"escaped": True, "alarm": False}
    assert daily.tier_of({**outcome_clean, "net": 299}, 300) == "clean"
    assert daily.tier_of({**outcome_clean, "net": 300}, 300) == "par"
    assert daily.tier_of({**outcome_clean, "net": 301}, 300) == "par"
    assert daily.tier_of({**outcome_clean, "net": -50}, 300) == "clean"


def test_merge_record_clamps_tries_and_handles_missing_keys():
    """merge_record increments tries (clamped to 999), takes max net, and defaults missing keys safely."""
    r = daily.merge_record(None, "clean", 500)
    assert r == {"tier": 2, "net": 500, "tries": 1}

    r = daily.merge_record(r, "par", 400)
    assert r["net"] == 500 and r["tries"] == 2

    # Test tries clamping at the limit
    big_old = {"tier": 1, "net": 100, "tries": 998}
    r = daily.merge_record(big_old, "busted", 0)
    assert r["tries"] == 999

    # Test missing keys default to 0 or 1 correctly
    empty_dict = {}
    r = daily.merge_record(empty_dict, "clean", 100)
    assert r == {"tier": 2, "net": 100, "tries": 1}
