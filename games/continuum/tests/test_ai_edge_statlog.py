"""Edge-case tests for statlog.py."""

import save
import statlog


def test_clean_rejects_non_list_input():
    """clean() should return an empty list for non-list inputs."""
    assert statlog.clean(None) == []
    assert statlog.clean("junk") == []
    assert statlog.clean(123) == []
    assert statlog.clean({"a": 1}) == []


def test_clean_rejects_bools_and_short_rows():
    """clean() drops rows containing booleans or wrong length."""
    row = [0.0] * len(statlog.COLUMN_KEYS)
    # Short row
    assert statlog.clean([row[:len(row) - 1]]) == []
    # Row with bool
    bad_row = list(row)
    bad_row[0] = True
    assert statlog.clean([bad_row]) == []


def test_clean_clamps_values_to_value_limit():
    """clean() clamps values to ±VALUE_LIMIT."""
    row = [0.0] * len(statlog.COLUMN_KEYS)
    row[0] = 1e9 + 1  # over limit
    row[1] = -1e9 - 1  # under limit
    cleaned = statlog.clean([row])
    assert cleaned[0][0] == 1e9
    assert cleaned[0][1] == -1e9


def test_clean_drops_season_zero():
    """clean() drops rows where season < 1."""
    row = [0.0] * len(statlog.COLUMN_KEYS)
    row[0] = 0  # season index is 0
    assert statlog.clean([row]) == []


def test_record_caps_history_at_max_rows():
    """record() keeps only the last MAX_ROWS entries."""
    c = save.Campaign()
    effects = c.tree.effects()
    report = c.state.advance_season(effects)
    ui = {}
    for _ in range(statlog.MAX_ROWS + 5):
        statlog.record(ui, c.state, effects, report, 0)
    assert len(ui[statlog.KEY]) == statlog.MAX_ROWS


def test_series_returns_empty_for_missing_key():
    """series() returns [] if the requested key is not in COLUMN_KEYS."""
    history = [[1.0] * len(statlog.COLUMN_KEYS)]
    assert statlog.series(history, "nonexistent_key") == []


def test_series_respects_count_parameter():
    """series() returns at most `count` items."""
    history = [[float(i)] * len(statlog.COLUMN_KEYS) for i in range(10)]
    result = statlog.series(history, "season", count=3)
    assert len(result) == 3
    assert result[-1] == 9.0


def test_format_value_handles_all_kinds():
    """format_value() formats int, pct, and num correctly."""
    assert statlog.format_value("population", 100) == "100"
    assert statlog.format_value("fed_pct", 85.5) == "86%"
    assert statlog.format_value("score", 42.3) == "42.3"


def test_format_delta_handles_zero_and_signs():
    """format_delta() shows arrow and sign correctly, or flat line for zero."""
    assert statlog.format_delta("population", 0) == "▬ 0"
    assert statlog.format_delta("population", 5) == "▲ +5"
    assert statlog.format_delta("livability", -2.5) == "▼ −2.5"
