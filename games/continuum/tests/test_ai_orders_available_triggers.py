"""Tests for orders.available_triggers()."""

import orders


def test_tribal_no_research_returns_only_free_triggers():
    """Normal case: Tribal era with no research unlocks only free triggers."""
    result = orders.available_triggers([], "tribal")
    assert set(result) == {"food_seasons", "idle"}


def test_later_era_with_research_includes_unlocked_trigger():
    """Normal case: Industrial era with required research unlocks advanced triggers."""
    researched = ["seasonal_rounds", "smoke_abatement"]
    result = orders.available_triggers(researched, "industrial")
    assert "land_health" in result
    assert "pollution" in result
    assert "sprawl" not in result


def test_none_researched_list_behaves_like_empty():
    """Edge case: Passing None for researched should not crash and behaves like an empty list."""
    result = orders.available_triggers(None, "tribal")
    assert set(result) == {"food_seasons", "idle"}
