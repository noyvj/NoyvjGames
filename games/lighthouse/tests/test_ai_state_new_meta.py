"""Tests for state.new_meta()."""

from state import new_meta


def test_new_meta_returns_expected_structure():
    """Check that the returned dictionary has all expected keys and correct default values."""
    meta = new_meta()
    expected_keys = {
        "nights_kept", "years", "ships_passed", "ships_delayed", "ships_damaged", "rescues",
        "lamp_ticks", "oil_used", "clean_streak", "best_clean_streak", "best_lamp_hours_year",
        "year_lamp_ticks", "counters", "achievements_earned", "story"
    }
    assert set(meta.keys()) == expected_keys
    assert meta["nights_kept"] == 0
    assert meta["oil_used"] == 0.0
    assert meta["counters"] == {}
    assert meta["achievements_earned"] == []
    assert set(meta["story"].keys()) == {"met", "letters", "gifts", "mysteries", "oddities"}


def test_new_meta_returns_independent_dicts():
    """Check that modifying one returned dict does not affect another (mutable default edge case)."""
    meta_a = new_meta()
    meta_b = new_meta()
    meta_a["nights_kept"] = 10
    meta_a["counters"]["test"] = 1
    meta_a["story"]["met"].append("sailor")
    assert meta_b["nights_kept"] == 0
    assert "test" not in meta_b["counters"]
    assert meta_b["story"]["met"] == []


def test_new_meta_story_lists_are_empty():
    """Check that every nested story list is present and empty."""
    meta = new_meta()
    for key in ("met", "letters", "gifts", "mysteries", "oddities"):
        assert isinstance(meta["story"][key], list)
        assert len(meta["story"][key]) == 0
