"""Edge-case tests for solver.py."""

import pytest

import gen
import solver


@pytest.fixture
def simple_chart():
    """Generate a valid open-water chart for testing solver limits."""
    c = gen.make_chart(1, 42)
    assert c is not None, "Failed to generate test chart"
    return c


def test_shoot_returns_none_when_start_equals_target(simple_chart):
    """shoot should return None if the target is the same as the start."""
    result = solver.shoot(simple_chart, (0.0, 0.0), (0.0, 0.0))
    assert result is None


def test_route_with_single_waypoint_returns_empty_legs(simple_chart):
    """route with only one waypoint should return no legs and the start position."""
    start = simple_chart["start"]
    legs, end = solver.route(simple_chart, [start])
    assert legs == []
    assert end == tuple(start)


def test_route_handles_large_wait_value(simple_chart):
    """route should accept a large wait value and prepend an anchor leg."""
    start = simple_chart["start"]
    target = simple_chart["dest"]
    legs, end = solver.route(simple_chart, [start, target], wait=100.0)
    assert len(legs) >= 1
    assert legs[0]["speed"] == 0.0
    assert legs[0]["hours"] == 100.0


def test_watch_route_with_zero_max_watches_returns_empty_legs(simple_chart):
    """watch_route with max_watches=0 should not sail any legs."""
    start = simple_chart["start"]
    target = simple_chart["dest"]
    legs = solver.watch_route(simple_chart, [start, target], max_watches=0)
    assert legs == []


def test_shoot_clamps_speed_to_chart_range(simple_chart):
    """shoot should only consider speeds within the chart's allowed range."""
    start = simple_chart["start"]
    target = (simple_chart["size"] + 100, simple_chart["size"] + 100)
    result = solver.shoot(simple_chart, start, target)
    assert result is not None
    lo, hi = simple_chart["speeds"]
    assert lo <= result["speed"] <= hi


def test_watch_route_with_small_watch_hours_sails_at_least_once(simple_chart):
    """watch_route with a small but valid watch_hours should still attempt at least one leg."""
    start = simple_chart["start"]
    target = simple_chart["dest"]
    legs = solver.watch_route(simple_chart, [start, target], watch_hours=0.5, max_watches=1)
    assert len(legs) >= 1
