"""Edge-case tests for explain.py: limits, empty inputs, and boundary values."""

import statlog

import explain


def _make_row(**overrides):
    """Build a stat row matching the game's format."""
    values = {key: 0.0 for key in statlog.COLUMN_KEYS}
    values["season"] = 1.0
    values.update(overrides)
    return [values[key] for key in statlog.COLUMN_KEYS]


def test_delta_returns_none_for_insufficient_history():
    """delta() should not crash on empty or single-row history."""
    assert explain.delta([], "food") is None
    assert explain.delta([_make_row()], "food") is None


def test_delta_returns_none_for_unknown_key():
    """delta() rejects keys that are not in the game's column list."""
    history = [_make_row(season=1.0, food=10.0), _make_row(season=2.0, food=15.0)]
    assert explain.delta(history, "nonexistent_col") is None


def test_delta_computes_correct_difference():
    """delta() correctly subtracts the second-to-last row from the last."""
    row_a = _make_row(season=1.0, food=10.0)
    row_b = _make_row(season=2.0, food=15.0)
    assert explain.delta([row_a, row_b], "food") == 5.0


def test_explain_returns_none_for_unexplainable_key():
    """explain() returns None for stats that have no honest breakdown."""
    history = [_make_row(season=1.0), _make_row(season=2.0)]
    assert explain.explain("equity", history, {"season": 2}) is None


def test_explain_handles_zero_net_change():
    """explain() returns a valid dict with zeroed factors when nothing changed."""
    history = [_make_row(season=1.0), _make_row(season=2.0)]
    out = explain.explain("food", history, {"season": 2})
    assert out is not None
    assert out["net"] == 0.0
    assert out["factors"] == []
    assert out["other"] == 0.0


def test_explain_falls_back_when_report_season_mismatches():
    """explain() falls back to 'Other changes' when the report season is stale."""
    row_a = _make_row(season=1.0, food=10.0)
    row_b = _make_row(season=2.0, food=20.0)
    report = {"season": 99, "food_gathered": 10.0}
    out = explain.explain("food", [row_a, row_b], report)
    assert out is not None
    labels = [label for label, _ in out["factors"]]
    assert "Other changes" in labels


def test_explain_works_with_effects_none():
    """explain() does not crash when effects are explicitly passed as None."""
    row_a = _make_row(season=1.0, food=10.0)
    row_b = _make_row(season=2.0, food=20.0)
    report = {"season": 2, "food_gathered": 10.0}
    out = explain.explain("food", [row_a, row_b], report, effects=None)
    assert out is not None
    assert out["net"] == 10.0


def test_amount_text_formats_positive_negative_and_zero():
    """amount_text() correctly applies signs and units."""
    assert explain.amount_text(5.0, "int") == "+5"
    assert explain.amount_text(-3.2, "num") == "−3.2"
    assert explain.amount_text(0.0, "pct") == "0.0 points"


def test_amount_text_handles_extreme_float_values():
    """amount_text() survives very large and very small floats without crashing."""
    large = explain.amount_text(1e30, "num")
    small = explain.amount_text(-1e-30, "num")
    assert len(large) > 0
    assert len(small) > 0


def test_waterfall_lines_handles_none_and_empty_factors():
    """waterfall_lines() returns an empty list for None input, and a net line for empty factors."""
    assert explain.waterfall_lines(None) == []
    empty_explained = {"key": "food", "label": "Food", "net": 0.0, "factors": [], "other": 0.0, "unit": "num"}
    lines = explain.waterfall_lines(empty_explained)
    assert len(lines) == 1
    assert "Net change" in lines[0]


def test_waterfall_geometry_bounds_for_extreme_values():
    """waterfall_geometry() keeps all bars inside the 0-100% track."""
    explained = {
        "key": "food",
        "label": "Food",
        "net": 100.0,
        "factors": [("Gathered", 100.0)],
        "other": 0.0,
        "unit": "num",
    }
    steps = explain.waterfall_geometry(explained)
    assert len(steps) == 2
    for step in steps:
        assert 0 <= step["left"] <= 100
        assert 0 < step["width"] <= 100
        assert step["left"] + step["width"] <= 100.1


def test_waterfall_geometry_handles_zero_net_change():
    """waterfall_geometry() assigns a minimum width when the net change is zero."""
    explained = {
        "key": "food",
        "label": "Food",
        "net": 0.0,
        "factors": [("Gathered", 50.0), ("Eaten", -50.0)],
        "other": 0.0,
        "unit": "num",
    }
    steps = explain.waterfall_geometry(explained)
    assert len(steps) == 3
    for step in steps:
        assert 0 < step["width"] <= 100
