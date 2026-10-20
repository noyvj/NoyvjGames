"""Edge-case tests for levels.py public functions."""

from levels import get_level, unlocked, allowed_chips, is_open, missing_chips, LEVELS, BY_ID


def test_get_level_returns_none_for_missing_ids():
    assert get_level("nonexistent") is None
    assert get_level(None) is None
    assert get_level("") is None


def test_get_level_returns_dict_for_valid_id():
    lv = get_level("both")
    assert isinstance(lv, dict)
    assert lv["id"] == "both"


def test_unlocked_with_empty_list():
    assert unlocked([]) == []


def test_unlocked_with_invalid_ids():
    result = unlocked(["fake1", "fake2"])
    assert result == []


def test_unlocked_ignores_duplicates():
    all_ids = [lv["id"] for lv in LEVELS] * 2
    result = unlocked(all_ids)
    expected = [lv["unlock"] for lv in LEVELS if lv["unlock"]]
    assert result == expected


def test_allowed_chips_for_level_without_unlock():
    first_lv = LEVELS[0]
    assert allowed_chips(first_lv, []) == []


def test_allowed_chips_filters_own_unlock():
    lv = BY_ID["toggle"]
    solved = [lv2["id"] for lv2 in LEVELS if lv2["unlock"]]
    result = allowed_chips(lv, solved)
    assert lv["unlock"] not in result


def test_is_open_for_level_with_no_needs():
    first_lv = LEVELS[0]
    assert is_open(first_lv, []) is True


def test_is_open_fails_when_needs_missing():
    lv = BY_ID["toggle"]
    assert is_open(lv, []) is False


def test_missing_chips_empty_solved():
    lv = BY_ID["toggle"]
    missing = missing_chips(lv, [])
    assert len(missing) > 0 and set(missing).issubset(set(lv["needs"]))


def test_missing_chips_all_present():
    lv = BY_ID["toggle"]
    solved = [lv2["id"] for lv2 in LEVELS if lv2["unlock"]]
    missing = missing_chips(lv, solved)
    assert missing == []
