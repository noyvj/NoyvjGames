"""Tests for get_level() in levels.py."""


from levels import get_level, BY_ID


def test_get_level_returns_the_correct_dict_for_a_known_id():
    result = get_level("both")
    assert result is not None
    assert result["id"] == "both"
    assert result is BY_ID["both"]


def test_get_level_returns_different_levels_for_different_ids():
    lv1 = get_level("odd-one-out")
    lv2 = get_level("comparator")
    assert lv1 is not None and lv2 is not None
    assert lv1["id"] != lv2["id"]
    assert lv1 is BY_ID["odd-one-out"]
    assert lv2 is BY_ID["comparator"]


def test_get_level_returns_none_for_unknown_id():
    result = get_level("nonexistent-level")
    assert result is None
