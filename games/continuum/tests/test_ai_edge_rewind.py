"""Edge-case tests for rewind.py."""

import rewind


def test_clean_empty_and_zero_inputs():
    """Test clean handles None, empty dict, and zero used."""
    assert rewind.clean(None) == {"used": 0}
    assert rewind.clean({}) == {"used": 0}
    assert rewind.clean({"used": 0}) == {"used": 0}


def test_clean_largest_allowed_values_are_clamped():
    """Test clean clamps values at and above MAX_USED."""
    assert rewind.clean({"used": float(rewind.MAX_USED)}) == {"used": rewind.MAX_USED}
    assert rewind.clean({"used": float(rewind.MAX_USED) + 1000}) == {"used": rewind.MAX_USED}


def test_clean_rejected_or_negative_values():
    """Test clean rejects strings and clamps negatives to zero."""
    assert rewind.clean({"used": -1}) == {"used": 0}
    assert rewind.clean({"used": -99.5}) == {"used": 0}
    assert rewind.clean({"used": "reject"}) == {"used": 0}


def test_get_empty_or_missing_ui():
    """Test get returns zero used for missing or empty UI."""
    assert rewind.get(None) == {"used": 0}
    assert rewind.get({}) == {"used": 0}
    assert rewind.get({"other_key": 1}) == {"used": 0}


def test_put_zero_used_removes_key_and_positive_sets_it():
    """Test put removes the key when used is zero, and sets it otherwise."""
    ui_with = {rewind.KEY: {"used": 5}}
    assert rewind.put(ui_with, {"used": 0}) == {"used": 0}
    assert rewind.KEY not in ui_with

    ui_empty = {}
    assert rewind.put(ui_empty, {"used": 1}) == {"used": 1}
    assert ui_empty[rewind.KEY] == {"used": 1}


def test_earned_tokens_zero_and_smallest_positive():
    """Test earned_tokens returns zero below threshold and one at threshold."""
    assert rewind.earned_tokens(0) == 0
    assert rewind.earned_tokens(4) == 0
    assert rewind.earned_tokens(5) == 1


def test_earned_tokens_largest_allowed_values_scale_correctly():
    """Test earned_tokens scales correctly for large achievement counts."""
    assert rewind.earned_tokens(10**6) == 200000
    assert rewind.earned_tokens(-100) == 0


def test_tokens_left_negative_result_is_clamped_to_zero():
    """Test tokens_left clamps negative results to zero."""
    ui = {rewind.KEY: {"used": 10}}
    assert rewind.tokens_left(ui, 5) == 0


def test_tokens_left_exact_match_and_positive_difference():
    """Test tokens_left returns zero on exact match and correct difference otherwise."""
    ui = {rewind.KEY: {"used": 5}}
    assert rewind.tokens_left(ui, 25) == 0
    assert rewind.tokens_left(ui, 30) == 1
