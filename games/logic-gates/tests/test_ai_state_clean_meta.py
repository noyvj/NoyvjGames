"""Tests for state.clean_meta(). Validates that untrusted save data is safely parsed and defaults are applied correctly."""

import levels
import state


def test_empty_data_returns_default_meta():
    """Passing an empty dict should yield a fresh meta with no levels, stats, or work saved."""
    result = state.clean_meta({})
    assert result == state.new_meta()


def test_valid_levels_and_stats_are_kept():
    """A properly structured save with one solved level and counters should preserve those values."""
    lid = levels.LEVELS[0]["id"]
    data = {
        "levels": {lid: {"solved": True, "chips": 3, "par": True}},
        "stats": {"chips": 10, "wires": 5},
        "current": lid,
    }
    result = state.clean_meta(data)
    assert result["levels"][lid]["solved"] is True
    assert result["levels"][lid]["chips"] == 3
    assert result["stats"]["chips"] == 10
    assert result["stats"]["wires"] == 5
    assert result["current"] == lid


def test_invalid_keys_are_dropped_gracefully():
    """Bad level IDs, wrong types for stats, and malformed tiers should be ignored without raising."""
    data = {
        "levels": {"nonexistent-level": {"solved": True}},
        "stats": "not a dict",
        "found": [True, -1, 300, 42],
        "tiers": {"easy": {"nonexistent-level": {"chips": 5}}},
        "current": "bad-id",
        "work": {"nonexistent-level": {"chips": []}},
    }
    result = state.clean_meta(data)
    assert "nonexistent-level" not in result["levels"]
    assert result["stats"]["chips"] == 0
    assert result["found"] == [42]
    assert result["current"] == levels.LEVELS[0]["id"]
    assert "nonexistent-level" not in result["work"]
