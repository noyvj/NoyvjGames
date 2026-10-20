"""Tests for par.start_population()."""


import par
import sim


def test_start_population_returns_correct_int_for_standard():
    """Normal case: standard scenario population matches config."""
    result = par.start_population("standard")
    assert isinstance(result, int)
    assert result == int(sim.scenario_config("standard")["population"])


def test_start_population_returns_correct_int_for_fertile():
    """Normal case: fertile scenario population matches config."""
    result = par.start_population("fertile")
    assert isinstance(result, int)
    assert result == int(sim.scenario_config("fertile")["population"])


def test_start_population_handles_frontier_and_refuge():
    """Normal cases: frontier and refuge populations match config."""
    for scenario in ("frontier", "refuge"):
        result = par.start_population(scenario)
        assert isinstance(result, int) and result > 0
        assert result == int(sim.scenario_config(scenario)["population"])


def test_start_population_returns_int_not_float():
    """Edge case: ensures the return type is strictly int, not float."""
    result = par.start_population("standard")
    assert type(result) is int
