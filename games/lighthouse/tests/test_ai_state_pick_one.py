"""Tests for pick_one() in state.py."""

from state import PHASES, MODES, pick_one


def test_pick_one_returns_value_when_it_is_in_choices():
    assert pick_one("evening", PHASES, "day") == "evening"


def test_pick_one_returns_default_when_value_is_not_in_choices():
    assert pick_one("sunset", PHASES, "day") == "day"


def test_pick_one_returns_default_for_non_string_input():
    assert pick_one(123, MODES, "year") == "year"
