"""Tests for meta_to_dict() in state.py."""

from state import meta_to_dict, new_meta


def test_meta_to_dict_filters_defaults_and_keeps_nonzero():
    """Normal case: non-default values are kept, defaults (0, 0.0, [], {}) are omitted."""
    meta = new_meta()
    meta["nights_kept"] = 5
    meta["years"] = 1
    meta["ships_passed"] = 10
    meta["oil_used"] = 42.5
    meta["counters"]["quiet_nights"] = 3
    meta["story"]["met"] = ["sailor_a"]
    meta["story"]["letters"] = ["letter_1"]

    result = meta_to_dict(meta)

    assert "nights_kept" in result and result["nights_kept"] == 5
    assert "years" in result and result["years"] == 1
    assert "ships_passed" in result and result["ships_passed"] == 10
    assert "oil_used" in result and result["oil_used"] == 42.5
    assert "counters" in result and result["counters"]["quiet_nights"] == 3
    assert "story" in result
    assert result["story"]["met"] == ["sailor_a"]
    assert result["story"]["letters"] == ["letter_1"]
    # Defaults should be absent
    assert "lamp_ticks" not in result
    assert "achievements_earned" not in result


def test_meta_to_dict_removes_empty_counters_and_story():
    """Edge case: when counters and story are empty/default, their keys are removed entirely."""
    meta = new_meta()

    result = meta_to_dict(meta)

    assert "counters" not in result
    assert "story" not in result
    assert "achievements_earned" not in result


def test_meta_to_dict_handles_multiple_counters_and_achievements():
    """Normal case: multiple counters and a list of achievements are preserved correctly."""
    meta = new_meta()
    meta["achievements_earned"] = ["ach1", "ach2"]
    meta["counters"]["quiet_nights"] = 5
    meta["counters"]["fog_clears"] = 2
    meta["story"]["mysteries"] = ["mystery_a"]

    result = meta_to_dict(meta)

    assert result["achievements_earned"] == ["ach1", "ach2"]
    assert result["counters"]["quiet_nights"] == 5
    assert result["counters"]["fog_clears"] == 2
    assert result["story"]["mysteries"] == ["mystery_a"]
