"""Tests for consulting.seasons_used()."""


import consulting
import save


def _fresh(case="smokestack"):
    c = save.Campaign()
    assert consulting.apply(c, case)
    return c


def test_seasons_used_returns_difference_when_current_is_ahead():
    """Normal case: current season is past the start season."""
    c = _fresh("sprawl")
    c.state.season = 10
    entry = consulting.get(c.ui)
    assert consulting.seasons_used(entry, c.state) == 9


def test_seasons_used_returns_zero_when_current_equals_start():
    """Normal case: current season matches the start season."""
    c = _fresh("smokestack")
    # apply() sets state.season to 1
    entry = consulting.get(c.ui)
    assert consulting.seasons_used(entry, c.state) == 0


def test_seasons_used_clamps_to_zero_when_current_is_behind():
    """Edge case: current season is before the start season (should not happen in play)."""
    c = _fresh("sprawl")
    c.state.season = 1
    # Simulate a future start season to trigger the max(0, ...) clamp
    c.ui["consulting"]["start_season"] = 5
    entry = consulting.get(c.ui)
    assert consulting.seasons_used(entry, c.state) == 0
