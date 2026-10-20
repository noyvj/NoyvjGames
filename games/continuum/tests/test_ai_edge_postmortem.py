"""Edge-case tests for postmortem.py public functions."""

import postmortem
import save
import trajectory


def test_when_handles_zero_and_negative_seasons():
    """when() clamps season to at least 1, so zero and negative should yield Year 1, Spring."""
    assert postmortem.when(0) == "Year 1, Spring"
    assert postmortem.when(-5) == "Year 1, Spring"


def test_when_handles_large_season_numbers():
    """when() correctly wraps large season counts into years and seasons."""
    # 32 seasons = 8 full years. Season 33 is Year 9, Spring.
    assert postmortem.when(33) == "Year 9, Spring"
    # 35 seasons = 8 full years + 3 seasons -> Year 9, Autumn
    assert postmortem.when(35) == "Year 9, Autumn"


def test_when_handles_float_seasons():
    """when() converts floats to int before processing."""
    assert postmortem.when(1.9) == "Year 1, Spring"
    assert postmortem.when(4.1) == "Year 1, Winter"


def test_biggest_drop_with_empty_and_single_point_series():
    """biggest_drop() returns None when there are fewer than two data points."""
    assert postmortem.biggest_drop([]) is None
    assert postmortem.biggest_drop([(10, 50.0, 10)]) is None


def test_biggest_drop_with_equal_values_and_increases():
    """biggest_drop() handles flat lines and population growth (negative drops)."""
    # All equal livability -> drop is 0.0 at index 1
    series = [(i, 80.0, 10) for i in range(1, 6)]
    drop = postmortem.biggest_drop(series)
    assert drop == (0.0, 1)

    # Increasing livability -> negative drops, should pick the largest (closest to zero)
    series_inc = [(i, 50.0 + i * 10, 10) for i in range(1, 6)]
    drop = postmortem.biggest_drop(series_inc)
    assert drop == (-10.0, 1)


def test_livability_series_with_empty_trajectory():
    """livability_series() returns an empty list when the campaign has no trajectory points."""
    c = save.Campaign()
    c.state.trajectory = []
    series = postmortem.livability_series(c)
    assert series == []


def test_livability_series_with_few_points():
    """livability_series() correctly maps a short trajectory to season indices."""
    c = save.Campaign()
    c.state.season = 4
    c.state.trajectory = [
        [1, 90.0, 5, 85.0],
        [2, 88.0, 6, 82.0],
        [3, 85.0, 7, 80.0],
    ]
    series = postmortem.livability_series(c)
    assert series == [(1, 85.0, 5), (2, 82.0, 6), (3, 80.0, 7)]


def test_build_with_missing_ui_keys():
    """build() degrades gracefully when ui is missing statlog or minutes keys."""
    c = save.Campaign()
    for _ in range(5):
        effects = c.tree.effects()
        report = c.state.advance_season(effects)
        c.state.record_score(80.0)
        trajectory.record(c.state, report, 80.0)

    report = postmortem.build(c)
    assert report["ready"] is True
    assert any("no per-season stat history" in n for n in report.get("notes", []))


def test_lines_with_non_dict_and_missing_keys():
    """lines() returns a safe list for invalid input or incomplete reports."""
    assert postmortem.lines(None) == []
    assert postmortem.lines("string") == []
    assert postmortem.lines({}) == ["Post-mortem"]

    partial = {"ready": True, "went_well": [], "went_wrong": [], "root_cause": None, "redo": [], "notes": []}
    out = postmortem.lines(partial)
    assert "What went well" in out
    assert "Nothing stood out yet." in out
    assert "What went wrong" in out
    assert "Nothing went badly wrong." in out
