"""Edge-case tests for sim.py."""

from sim import clean_leg, clean_legs, plan_hours, plan_distance, compass_error, current_at, sail
from tests.golden_charts import GOLDEN_A


def test_clean_leg_rejects_non_dict_inputs():
    """Non-dict legs should be rejected and return None."""
    assert clean_leg(GOLDEN_A, "heading") is None
    assert clean_leg(GOLDEN_A, 123) is None
    assert clean_leg(GOLDEN_A, None) is None


def test_clean_leg_clamps_heading_to_0_359():
    """Headings outside 0-359 should wrap around."""
    leg = clean_leg(GOLDEN_A, {"heading": 360, "speed": 5, "hours": 1})
    assert leg["heading"] == 0
    leg = clean_leg(GOLDEN_A, {"heading": -10, "speed": 5, "hours": 1})
    assert leg["heading"] == 350


def test_clean_leg_clamps_speed_and_hours():
    """Speed and hours must be clamped to the chart's range and stepped by 0.5."""
    lo, _ = GOLDEN_A["speeds"]
    # Speed below lo should clamp to lo (stepped to SPEED_STEP)
    leg = clean_leg(GOLDEN_A, {"heading": 90, "speed": 0.1, "hours": 1})
    assert leg["speed"] == lo
    # Speed above hi
    leg = clean_leg(GOLDEN_A, {"heading": 90, "speed": 15, "hours": 1})
    assert leg["speed"] == GOLDEN_A["speeds"][1]
    # Hours below LEG_STEP (0.5)
    leg = clean_leg(GOLDEN_A, {"heading": 90, "speed": 5, "hours": 0.1})
    assert leg["hours"] == 0.5
    # Hours above MAX_LEG_HOURS (12.0)
    leg = clean_leg(GOLDEN_A, {"heading": 90, "speed": 5, "hours": 20})
    assert leg["hours"] == 12.0


def test_clean_leg_zero_speed_means_anchor():
    """Speed <= 0 should be forced to 0.0 (lie at anchor)."""
    leg = clean_leg(GOLDEN_A, {"heading": 90, "speed": -5, "hours": 1})
    assert leg["speed"] == 0.0
    leg = clean_leg(GOLDEN_A, {"heading": 90, "speed": 0, "hours": 1})
    assert leg["speed"] == 0.0


def test_clean_legs_respects_limit_and_filters_types():
    """clean_legs should truncate to limit and skip invalid legs."""
    legs = [{"heading": i, "speed": 5, "hours": 1} for i in range(10)] + ["bad"]
    cleaned = clean_legs(GOLDEN_A, legs, limit=3)
    assert len(cleaned) == 3
    assert all(isinstance(leg, dict) for leg in cleaned)


def test_plan_hours_and_distance_with_empty_legs():
    """Empty leg lists should return zero hours and distance."""
    assert plan_hours([]) == 0
    assert plan_distance([]) == 0


def test_compass_error_handles_missing_compass_and_nominal_model():
    """Missing compass or nominal model should yield zero error."""
    chart_no_compass = dict(GOLDEN_A, compass=None)
    assert compass_error(chart_no_compass, "true") == 0.0
    assert compass_error(GOLDEN_A, "nominal") == 0.0


def test_current_at_outside_rect_and_nominal_model():
    """Current should be zero outside the zone's rectangle or in nominal model."""
    chart = dict(GOLDEN_A, currents=[{"id": "c1", "rect": [0, 0, 5, 5], "set": 90, "drift_range": [1.0, 2.0]}])
    assert current_at(chart, (10, 10), 0.0, "true") == (0.0, 0.0)
    assert current_at(chart, (1, 1), 0.0, "nominal") == (0.0, 0.0)


def test_sail_with_empty_legs():
    """Sailing with no legs should return the start position and zero hours."""
    result = sail(GOLDEN_A, [])
    assert result["hours"] == 0.0
    assert result["aground"] is None
    assert result["legs_sailed"] == 0
    assert len(result["track"]) == 1


def test_sail_with_zero_speed_leg():
    """A leg with speed 0 should hold position but accumulate time."""
    chart = dict(GOLDEN_A, start=[0.0, 0.0], dest=[10.0, 10.0])
    legs = [{"heading": 90, "speed": 0, "hours": 2}]
    result = sail(chart, legs)
    assert result["end"] == [0.0, 0.0]
    assert abs(result["hours"] - 2.0) < 1e-6
