"""Edge-case tests for forecast.py (test_ai_edge_forecast.py).

Tests limits of the public API: empty states, epsilon boundaries, unknown keys,
and extreme values that the code actually handles.
"""


import forecast
import sim


def make_state(era="tribal", population=10, **allocation):
    state = sim.CityState(era=era)
    state.population = population
    for role in state.allocation:
        state.allocation[role] = 0
    state.allocation.update(allocation)
    return state


def test_preview_handles_empty_settlement():
    """preview should not crash on a settlement with zero population and no workers."""
    state = make_state(population=0)
    view = forecast.preview(state)
    assert view["population"]["delta"] == 0
    assert view["food"]["gathered"] == 0
    assert view["land_health"]["delta"] == 0


def test_preview_with_none_effects():
    """preview must accept effects=None without crashing or mutating state."""
    state = make_state(population=5, foragers=2)
    before_pop = state.population
    view = forecast.preview(state, effects=None)
    assert view["population"]["now"] == before_pop
    assert set(view.keys()) == set(forecast.KEYS)


def test_lines_unknown_key_returns_empty_list():
    """lines must return [] for any key not in forecast.KEYS."""
    assert forecast.lines("nonexistent", {}) == []
    assert forecast.lines("", {}) == []
    assert forecast.lines(None, {}) == []


def test_lines_land_health_steady_vs_changing():
    """Zero delta reads as steady; non-zero delta shows a sign and reason."""
    view_steady = {"now": 1.0, "delta": 0.0, "extraction": 10.0, "sustainable_yield": 26.0}
    view_changing = {"now": 0.8, "delta": -0.03, "extraction": 30.0, "sustainable_yield": 26.0}

    text_steady = forecast.lines("land_health", view_steady)
    text_changing = forecast.lines("land_health", view_changing)

    assert "steady" in text_steady[0]
    assert any(sign in text_changing[0] for sign in ["+", "-"])


def test_lines_population_growth_stalled_no_room():
    """When growth progress doesn't advance and housing is full, wording should reflect no change."""
    view = {
        "now": 8, "housing": 8.0, "delta": 0, "births": 0, "deaths": 0, "idle": 0,
        "growth_before": 0.9, "growth_after": 0.9
    }
    text = forecast.lines("population", view)
    assert text[0] == "No change per season"


def test_preview_with_extreme_population():
    """preview should handle very large population numbers without crashing or returning NaN."""
    state = make_state(population=10000, foragers=500, gatherers=500)
    view = forecast.preview(state)
    assert view["population"]["now"] == 10000
    assert view["population"]["delta"] is not None
    assert "nan" not in str(view["population"]["delta"]).lower()
