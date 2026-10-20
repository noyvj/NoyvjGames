"""Edge-case tests for consulting.py."""

import consulting
import save


def test_clean_rejects_zero_start_season():
    raw = {"case": "smokestack", "start_season": 0, "streak": 0, "result": None}
    assert consulting.clean(raw) is None


def test_clean_rejects_empty_dict():
    assert consulting.clean({}) is None


def test_clean_clamps_start_season_to_max():
    raw = {"case": "smokestack", "start_season": 10**7 + 5, "streak": 0, "result": None}
    cleaned = consulting.clean(raw)
    assert cleaned["start_season"] == 10**7


def test_clean_clamps_streak_to_hold_seasons():
    raw = {"case": "smokestack", "start_season": 1, "streak": 100, "result": None}
    cleaned = consulting.clean(raw)
    assert cleaned["streak"] == consulting.HOLD_SEASONS


def test_seasons_used_returns_zero_when_past_start():
    entry = {"case": "smokestack", "start_season": 5}

    class FakeState:
        season = 2

    assert consulting.seasons_used(entry, FakeState()) == 0


def test_status_text_returns_empty_for_none_entry():
    class FakeState:
        pass

    assert consulting.status_text(None, FakeState()) == ""


def test_apply_rejects_invalid_case_id():
    c = save.Campaign()
    assert consulting.apply(c, "nonexistent") is False


def test_abandon_returns_false_when_no_case_active():
    c = save.Campaign()
    assert consulting.abandon(c) is False
