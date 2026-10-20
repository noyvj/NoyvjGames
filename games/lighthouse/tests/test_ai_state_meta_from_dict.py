"""Tests for state.meta_from_dict()."""

from state import meta_from_dict, new_meta


def test_normal_case_parses_counters_and_story():
    raw = {
        "nights_kept": 10,
        "oil_used": 50.5,
        "counters": {"quiet_nights": 5, "fog_clears": 3},
        "story": {"met": [], "letters": [], "gifts": [], "mysteries": [], "oddities": []}
    }
    result = meta_from_dict(raw)
    assert result["nights_kept"] == 10
    assert result["oil_used"] == 50.5
    assert result["counters"]["quiet_nights"] == 5
    assert result["story"]["met"] == []


def test_normal_case_deduplicates_and_caps_achievements():
    """Deduplication and the 80-item cap both work correctly."""
    raw = {
        "achievements_earned": ["a", "a"] + ["ach_" + str(i).zfill(3) for i in range(90)]
    }
    result = meta_from_dict(raw)
    assert len(result["achievements_earned"]) == 80
    assert result["achievements_earned"][0] == "a"


def test_edge_case_empty_dict_returns_default_meta():
    raw = {}
    default = new_meta()
    result = meta_from_dict(raw)
    assert result["nights_kept"] == default["nights_kept"]
    assert result["oil_used"] == default["oil_used"]
    assert result["counters"] == default["counters"]
    assert result["story"]["met"] == default["story"]["met"]
