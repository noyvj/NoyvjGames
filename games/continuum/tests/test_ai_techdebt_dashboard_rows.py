"""Tests for techdebt.dashboard_rows()."""

import techdebt


def _make_state(buildings=None):
    """Helper to create a minimal state object with a .buildings dict."""
    class State:
        pass
    state = State()
    state.buildings = buildings or {}
    return state


def test_zero_debt():
    """When debt is zero, upkeep and outages should be zero and refactor not scheduled."""
    state = _make_state({"shelter": 5})
    record = techdebt.fresh()
    rows = techdebt.dashboard_rows(state, record)
    assert len(rows) == 4
    assert rows[0] == ("Technical debt", "0% (none)")
    assert rows[1] == ("Debt upkeep", "0.0 materials a season")
    assert rows[2] == ("Output lost to outages", "0%")
    assert rows[3] == ("Refactor season", "not scheduled")


def test_medium_debt_with_refactor():
    """With 30% debt and a refactor scheduled, upkeep and outages reflect the values."""
    state = _make_state({"shelter": 10, "granary": 5})
    record = techdebt.fresh()
    record["debt"] = 0.3
    record["refactor"] = True
    rows = techdebt.dashboard_rows(state, record)
    assert len(rows) == 4
    assert rows[0] == ("Technical debt", "30% (building up)")
    assert rows[1] == ("Debt upkeep", "1.1 materials a season")
    assert rows[2] == ("Output lost to outages", "12%")
    assert rows[3] == ("Refactor season", "scheduled for next season")


def test_high_debt_edge_case():
    """At 100% debt with zero buildings, upkeep is zero but outages hit the cap."""
    state = _make_state({"shelter": 0})
    record = techdebt.fresh()
    record["debt"] = 1.0
    rows = techdebt.dashboard_rows(state, record)
    assert len(rows) == 4
    assert rows[0] == ("Technical debt", "100% (high)")
    assert rows[1] == ("Debt upkeep", "0.0 materials a season")
    assert rows[2] == ("Output lost to outages", "30%")
    assert rows[3] == ("Refactor season", "not scheduled")
