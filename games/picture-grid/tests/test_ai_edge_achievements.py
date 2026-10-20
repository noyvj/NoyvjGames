"""Edge-case tests for achievements.py."""

import achievements
import pictures


def test_facts_of_with_empty_and_zero_inputs():
    """facts_of should handle empty dicts and zero fills gracefully."""
    facts = achievements.facts_of({}, {}, 0, False)
    assert facts["hung"] == 0
    assert facts["cells"] == 0
    assert facts["slides"] == 0
    assert facts["big"] == 0
    assert facts["clean"] == 0
    for g in range(len(pictures.GALLERIES)):
        assert facts["gal%d" % g] == 0


def test_facts_of_with_large_inputs():
    """facts_of should handle maximum gallery sizes and large fill counts."""
    all_solved = {p.id: 1 for p in pictures.ALL}
    facts = achievements.facts_of(all_solved, {}, 999999, True)
    assert facts["hung"] == len(pictures.ALL)
    assert facts["cells"] == 999999
    assert facts["slides"] == 1
    assert facts["big"] >= 1
    for g in range(len(pictures.GALLERIES)):
        assert facts["gal%d" % g] == len(pictures.GALLERIES[g]["pictures"])


def test_earned_boundary_conditions():
    """earned should trigger exactly at the need value, not below."""
    facts_below = {"hung": 0, "gal0": 9, "big": 0, "clean": 9, "slides": 0, "cells": 9999}
    assert achievements.earned(facts_below) == []

    # Check specific boundaries for key achievements
    facts_at_need = {"hung": 1, "gal0": 10, "big": 1, "clean": 10, "slides": 1, "cells": 10000}
    earned_ids = achievements.earned(facts_at_need)
    assert "first_frame" in earned_ids
    assert "small_hands" in earned_ids
    assert "big_one" in earned_ids
    assert "clean_lines" in earned_ids
    assert "slow_light" in earned_ids
    assert "ten_thousand" in earned_ids


def test_earned_with_empty_facts():
    """earned should return an empty list when no facts are provided."""
    assert achievements.earned({}) == []


def test_view_with_empty_facts():
    """view should return correct structure with zero progress for all achievements."""
    view_list = achievements.view({})
    assert len(view_list) == 14
    for entry in view_list:
        assert entry["have"] == 0
        assert entry["earned"] is False
        assert entry["need"] > 0


def test_view_with_exceeding_values():
    """view should clamp 'have' to 'need' when facts exceed the requirement."""
    facts = {"hung": 100, "gal0": 50, "gal1": 50, "gal2": 50, "gal3": 50, "gal4": 50, "gal5": 50, "big": 10, "clean": 20, "slides": 1, "cells": 50000}
    view_list = achievements.view(facts)
    for entry in view_list:
        assert entry["have"] == entry["need"]
        assert entry["earned"] is True
