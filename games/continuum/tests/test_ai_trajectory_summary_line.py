"""Tests for trajectory.summary_line()."""

import sim
import trajectory


def test_empty_points_returns_prompt():
    assert trajectory.summary_line([]) == "Advance a season to start the chart."


def test_single_point_formats_correctly():
    era_name = sim.ERA_ORDER[0]
    ref_val = trajectory.reference_index(era_name)
    points = [[2.5, 0.0, 10.0, 80.0]]
    result = trajectory.summary_line(points)
    assert "Now: 2.5x subsistence output per person." in result
    assert f"({trajectory.REFERENCE[era_name][0]}): {ref_val:.1f}x the year-1 CE level." in result


def test_multiple_points_uses_last():
    era_name = sim.ERA_ORDER[2]
    ref_val = trajectory.reference_index(era_name)
    points = [[1.0, 0.0, 5.0, 50.0], [4.5, 2.0, 20.0, 75.0]]
    result = trajectory.summary_line(points)
    assert "Now: 4.5x subsistence output per person." in result
    assert f"({trajectory.REFERENCE[era_name][0]}): {ref_val:.1f}x the year-1 CE level." in result


def test_zero_values_format_correctly():
    era_name = sim.ERA_ORDER[0]
    ref_val = trajectory.reference_index(era_name)
    points = [[0.0, 0.0, 0.0, 0.0]]
    result = trajectory.summary_line(points)
    assert "Now: 0.0x subsistence output per person." in result
    assert f"({trajectory.REFERENCE[era_name][0]}): {ref_val:.1f}x the year-1 CE level." in result
