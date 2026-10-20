"""Edge-case tests for trajectory.py."""

import trajectory
import sim


def test_output_index_handles_zero_population():
    report = {"food_gathered": 10.0, "materials_gathered": 0.0, "tools_made": 0.0, "knowledge_made": 0.0}
    # The code clamps population to 1 to avoid division by zero, so it returns a valid index instead of 0.
    assert trajectory.output_index(report, 0) == 5.0


def test_output_index_handles_missing_report_keys():
    report = {}
    assert trajectory.output_index(report, 5) == 0.0


def test_output_index_handles_non_finite_values():
    report = {"food_gathered": float("inf"), "materials_gathered": 0.0, "tools_made": 0.0, "knowledge_made": 0.0}
    assert trajectory.output_index(report, 5) == 0.0


def test_reference_index_returns_default_for_unknown_era():
    assert trajectory.reference_index("nonexistent") == 1.0


def test_reference_index_handles_empty_string():
    assert trajectory.reference_index("") == 1.0


def test_clean_points_rejects_non_list_input():
    assert trajectory.clean_points(None) == []
    assert trajectory.clean_points(42) == []
    assert trajectory.clean_points("x") == []


def test_clean_points_clamps_era_bounds():
    raw = [[1.0, -5.0, 10.0, 50.0], [1.0, 999.0, 20.0, 60.0]]
    cleaned = trajectory.clean_points(raw)
    assert len(cleaned) == 2
    assert cleaned[0][1] == 0.0
    assert cleaned[1][1] == float(len(sim.ERA_ORDER) - 1)


def test_clean_points_clamps_livability_bounds():
    raw = [[1.0, 0.0, 10.0, -10.0], [1.0, 0.0, 20.0, 150.0]]
    cleaned = trajectory.clean_points(raw)
    assert cleaned[0][3] == 0.0
    assert cleaned[1][3] == 100.0


def test_current_output_index_handles_missing_last_report():
    class FakeState:
        last_report = None
    assert trajectory.current_output_index(FakeState()) is None


def test_summary_line_with_empty_points():
    assert trajectory.summary_line([]) == "Advance a season to start the chart."


def test_trajectory_svg_with_empty_points():
    assert trajectory.trajectory_svg([]) == ""


def test_scatter_svg_with_empty_points():
    assert trajectory.scatter_svg([]) == ""
