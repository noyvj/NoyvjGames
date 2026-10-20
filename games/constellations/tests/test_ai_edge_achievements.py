"""Edge-case tests for achievements.py."""

import achievements
import charts


def test_facts_of_empty_inputs():
    """facts_of with empty solved, hinted, and zero draws returns all zeros."""
    facts = achievements.facts_of({}, {}, 0)
    assert all(v == 0 for v in facts.values())
    assert set(facts.keys()) == set(achievements.FACTS)


def test_facts_of_huge_draws():
    """facts_of handles very large draw counts without error or overflow."""
    huge_draws = 10**9
    facts = achievements.facts_of({}, {}, huge_draws)
    assert facts["lines"] == huge_draws


def test_earned_empty_and_thresholds():
    """earned returns no ids for empty facts, and triggers exactly at thresholds."""
    assert achievements.earned({}) == []

    # Smallest threshold: first_figure needs 1
    assert "first_figure" in achievements.earned({"found": 1})
    assert "first_figure" not in achievements.earned({"found": 0})

    # Largest threshold: forty_figures needs TOTAL (40)
    assert "forty_figures" in achievements.earned({"found": 40})
    assert "forty_figures" not in achievements.earned({"found": 39})


def test_view_clamps_have_to_need():
    """view clamps the 'have' count to 'need' so it never exceeds it."""
    facts = {"found": 100, "lines": 9999, "hunter": 5, "bears": 10, "cross": 2}
    view_list = achievements.view(facts)
    for entry in view_list:
        assert entry["have"] <= entry["need"], f"{entry['id']} have {entry['have']} exceeds need {entry['need']}"


def test_view_handles_missing_keys_gracefully():
    """view treats missing keys in facts as zero and does not raise."""
    partial_facts = {"lines": 100}
    view_list = achievements.view(partial_facts)
    for entry in view_list:
        assert "have" in entry and "need" in entry
        if entry["id"] != "long_night":
            assert entry["have"] == 0, f"{entry['id']} should be 0 but got {entry['have']}"


def test_facts_of_partial_seasons_with_real_ids():
    """facts_of correctly counts partial season progress using real chart IDs."""
    season0_charts = charts.SEASONS[0]["charts"]
    partial_solved = {c["id"] for c in season0_charts[:3]}
    facts = achievements.facts_of(partial_solved, {}, 0)
    assert facts["sea0"] == 3
    assert facts["sea1"] == 0
