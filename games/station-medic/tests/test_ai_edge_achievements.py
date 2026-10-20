"""Edge-case tests for achievements.py."""

import achievements


def test_earned_with_empty_facts_returns_empty_list():
    """When no facts are provided, no achievements should be earned."""
    assert achievements.earned({}) == []


def test_earned_with_all_facts_met_excludes_need_zero():
    """When all tracked facts exceed their thresholds, only achievements with need > 0 are returned."""
    facts = {a[3]: 10**6 for a in achievements.ACHIEVEMENTS}
    earned_ids = achievements.earned(facts)
    expected_count = sum(1 for a in achievements.ACHIEVEMENTS if a[4] > 0)
    assert len(earned_ids) == expected_count


def test_view_with_empty_facts_shows_zero_have():
    """When facts are empty, every achievement should show have=0."""
    view_list = achievements.view({})
    assert all(a["have"] == 0 for a in view_list)


def test_view_clamps_have_to_need_for_huge_facts():
    """When a fact value exceeds the need, have should be clamped to need."""
    facts = {a[3]: 10**9 for a in achievements.ACHIEVEMENTS}
    view_list = achievements.view(facts)
    for a in view_list:
        assert a["have"] == a["need"]


def test_goals_with_no_open_chapters_returns_empty():
    """When no chapters are open, goals should be an empty list."""
    facts = {a[3]: 0 for a in achievements.ACHIEVEMENTS}
    assert achievements.goals(facts, 0) == []


def test_goals_with_zero_count_returns_empty():
    """When count is 0, goals should return an empty list regardless of facts."""
    facts = {a[3]: 0 for a in achievements.ACHIEVEMENTS}
    assert achievements.goals(facts, 8, count=0) == []
