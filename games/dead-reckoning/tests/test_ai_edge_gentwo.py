"""Edge-case tests for gentwo.py."""

import gentwo


def _make_chart(size=10.0, start=(2.0, 2.0), dest=(8.0, 8.0), arrival_radius=1.0, hazards=None, land=None):
    """Build a minimal chart dict matching the structure expected by gentwo."""
    return {
        "start": list(start),
        "dest": list(dest),
        "size": size,
        "arrival_radius": arrival_radius,
        "hazards": hazards or [],
        "land": land or [],
        "speeds": [3.0, 4.0, 5.0],
        "seed": 12345,
    }


def test_add_second_ship_returns_none_when_start_and_dest_are_identical():
    """Test that identical start and dest coordinates are rejected."""
    chart = _make_chart(start=(5.0, 5.0), dest=(5.0, 5.0))
    result = gentwo.add_second_ship(chart, "open", 42, 0)
    assert result is None


def test_add_second_ship_handles_zero_chart_size():
    """Test that a chart with zero size does not cause division by zero."""
    chart = _make_chart(size=0.0)
    result = gentwo.add_second_ship(chart, "open", 42, 0)
    assert result is None


def test_add_second_ship_handles_hazards_overlapping_start_and_dest():
    """Test that hazards overlapping the endpoints prevent valid generation."""
    chart = _make_chart(
        start=(5.0, 5.0),
        dest=(6.0, 6.0),
        hazards=[{"x": 5.0, "y": 5.0, "r": 2.0}]
    )
    result = gentwo.add_second_ship(chart, "open", 42, 0)
    assert result is None


def test_add_second_ship_handles_very_small_chart_dimensions():
    """Test that clamping in _endpoints handles charts near the minimum viable size."""
    chart = _make_chart(size=1.0)
    result = gentwo.add_second_ship(chart, "open", 42, 0)
    assert result is None or isinstance(result, dict)
