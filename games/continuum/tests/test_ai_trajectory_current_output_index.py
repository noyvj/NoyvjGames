"""Tests for trajectory.current_output_index()."""

import save
import sim
import trajectory


def _make_state(last_report=None, population=10):
    """Create a minimal CityState for testing current_output_index."""
    c = save.Campaign()
    if last_report is not None:
        c.state.last_report = last_report
    c.state.population = population
    return c.state


def test_normal_report_returns_correct_multiple():
    """A standard report with known values should yield the expected output index."""
    state = _make_state(
        last_report={
            "food_gathered": 100.0,
            "materials_gathered": 50.0,
            "tools_made": 20.0,
            "knowledge_made": 30.0,
        },
        population=10,
    )
    result = trajectory.current_output_index(state)
    total = 100 + 50 + 20 + 30
    expected = total / 10 / sim.FOOD_PER_PERSON
    assert result == expected


def test_zero_values_returns_zero():
    """A report with all zeros should return 0.0."""
    state = _make_state(
        last_report={
            "food_gathered": 0.0,
            "materials_gathered": 0.0,
            "tools_made": 0.0,
            "knowledge_made": 0.0,
        },
        population=5,
    )
    assert trajectory.current_output_index(state) == 0.0


def test_missing_report_returns_none():
    """When last_report is not a dict (e.g., None), it should return None."""
    state = _make_state(last_report=None, population=10)
    assert trajectory.current_output_index(state) is None


def test_invalid_report_values_returns_zero():
    """Malformed report values that raise TypeError or ValueError should fall back to 0.0."""
    state = _make_state(
        last_report={
            "food_gathered": "not a number",
            "materials_gathered": 10.0,
            "tools_made": 5.0,
            "knowledge_made": 2.0,
        },
        population=4,
    )
    assert trajectory.current_output_index(state) == 0.0
