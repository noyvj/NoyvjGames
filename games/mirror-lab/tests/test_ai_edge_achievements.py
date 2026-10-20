"""Edge-case tests for achievements.py public functions."""


import achievements
import benches


def test_facts_empty_input_returns_zeros():
    """facts({}) should return all counters at zero."""
    result = achievements.facts({})
    assert result["cleared"] == 0
    assert result["fewest"] == 0
    assert result["turns"] == 0
    assert result["light_both"] == 0
    assert result["decoy"] == 0
    for number in range(1, len(benches.CHAPTERS) + 1):
        assert result[f"ch{number}"] == 0


def test_earned_zero_input_returns_empty_list():
    """earned({}) should return an empty list when no facts are met."""
    assert achievements.earned({}) == []


def test_view_zero_input_has_nothing_earned():
    """view({}) should show have=0 and earned=False for every achievement."""
    view = achievements.view({})
    for entry in view:
        assert entry["have"] == 0
        assert entry["earned"] is False
        assert entry["need"] > 0


def test_summary_zero_input_shows_zero_text():
    """summary({}) should return the correct zero-text format."""
    result = achievements.summary({})
    assert result["earned"] == 0
    assert result["total"] == achievements.TOTAL_ACHIEVEMENTS
    assert result["text"] == f"0 of {achievements.TOTAL_ACHIEVEMENTS} achievements earned"


def test_earned_exceeding_needs_returns_all_ids():
    """Passing values larger than any need should still return all achievement IDs."""
    huge = {"cleared": 1000, "fewest": 1000, "turns": 1000, "light_both": 1000, "decoy": 1000}
    for number in range(1, len(benches.CHAPTERS) + 1):
        huge[f"ch{number}"] = 1000
    assert achievements.earned(huge) == list(achievements.IDS)


def test_view_clamps_have_to_need():
    """view() clamps have to need when fact values exceed it."""
    view = achievements.view({"cleared": 100})
    first_beam = next(e for e in view if e["id"] == "first_beam")
    assert first_beam["have"] == 1


def test_view_missing_keys_defaults_to_zero():
    """view() should treat missing fact keys as zero, not raise KeyError."""
    partial = {"cleared": 5}
    view = achievements.view(partial)
    # fewest_pieces relies on "fewest", which is missing in partial
    fewest_entry = next(e for e in view if e["id"] == "fewest_pieces")
    assert fewest_entry["have"] == 0
