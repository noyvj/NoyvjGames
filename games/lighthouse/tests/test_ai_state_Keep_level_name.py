"""Tests for Keep.level_name() in state.py."""

from data import LEVELS
from state import Keep


def test_level_name_returns_correct_names_for_valid_indices():
    """Normal cases: indices 0, 1, and 2 should return the corresponding entries from LEVELS."""
    keeper = Keep(seed=1)
    for i in range(3):
        assert keeper.level_name(i) == LEVELS[i]


def test_level_name_returns_last_valid_entry():
    """Normal case: index equal to len(LEVELS) - 1 should return the last level name."""
    keeper = Keep(seed=1)
    expected_index = len(LEVELS) - 1
    assert keeper.level_name(expected_index) == LEVELS[expected_index]


def test_level_name_raises_on_out_of_bounds():
    """Edge case: an index beyond the list bounds should raise IndexError."""
    keeper = Keep(seed=1)
    try:
        keeper.level_name(len(LEVELS))
        assert False, "Expected IndexError"
    except IndexError:
        pass
