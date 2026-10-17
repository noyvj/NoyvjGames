"""Tests for kit.parse_cond()."""

import kit


def test_single_flag_parses_to_all():
    """A single flag string should appear in the 'all' list."""
    cond = kit.parse_cond("bit")
    assert cond["all"] == ["bit"]
    assert cond["none"] == []
    assert cond["min"] == {}
    assert cond["max"] == {}


def test_mixed_flags_and_stats_parses_correctly():
    """Combining flags, stat minimums, and stat maximums works as documented."""
    cond = kit.parse_cond("bit&!battery&t4&h<5")
    assert cond["all"] == ["bit"]
    assert cond["none"] == ["battery"]
    assert cond["min"] == {"trust": 4}
    assert cond["max"] == {"hope": 5}


def test_empty_or_none_input_returns_none():
    """Edge case: empty strings and None should return None."""
    assert kit.parse_cond("") is None
    assert kit.parse_cond(None) is None
