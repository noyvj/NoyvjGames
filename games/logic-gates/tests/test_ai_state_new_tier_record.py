"""Tests for new_tier_record() in state.py."""

import state


def test_new_tier_record_returns_correct_default_structure():
    rec = state.new_tier_record()
    assert isinstance(rec, dict)
    assert set(rec.keys()) == {"chips", "par"}
    assert rec["chips"] is None
    assert rec["par"] is False


def test_new_tier_record_values_are_exactly_none_and_false():
    rec = state.new_tier_record()
    assert rec["chips"] is None
    assert rec["par"] is False


def test_new_tier_record_returns_independent_dicts_on_repeated_calls():
    rec1 = state.new_tier_record()
    rec2 = state.new_tier_record()
    assert rec1 is not rec2
    rec1["chips"] = 5
    assert rec2["chips"] is None
