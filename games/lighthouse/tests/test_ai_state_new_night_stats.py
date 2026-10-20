"""Tests for state.new_night_stats()."""

from state import new_night_stats


def test_new_night_stats_returns_all_expected_keys_and_defaults():
    """Verify the dictionary contains every key with its correct default value."""
    stats = new_night_stats()
    expected = {
        "oil_used": 0.0, "lamp_ticks": 0, "incidents": 0, "unhandled": 0,
        "damage": 0, "delayed": 0, "damaged": 0, "passed": 0,
        "rep": 0, "salvage": 0, "dark": False, "stopped": False,
        "ration_hit": False, "worst_cond": 0, "fog_ticks": 0,
        "events": 0, "wound": 0, "rescued": 0, "mail_landed": False,
    }
    assert stats == expected


def test_new_night_stats_types_match_defaults():
    """Ensure numeric defaults are ints/floats and boolean flags are actually bools."""
    stats = new_night_stats()
    assert isinstance(stats["oil_used"], float)
    assert isinstance(stats["lamp_ticks"], int)
    assert isinstance(stats["dark"], bool)
    assert isinstance(stats["mail_landed"], bool)


def test_new_night_stats_produces_independent_dicts():
    """Edge case: mutating one result must not affect the next call."""
    stats_a = new_night_stats()
    stats_b = new_night_stats()
    stats_a["lamp_ticks"] = 99
    assert stats_b["lamp_ticks"] == 0
