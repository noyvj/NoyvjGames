"""Tests for walker.visible() function."""

import walker


def test_visible_all_lines_shown_when_no_conditions():
    """visible returns all texts when every line has a None condition."""
    state, _ = walker.initial()
    lines = [(None, "Line A"), (None, "Line B")]
    result = walker.visible(lines, state)
    assert result == ["Line A", "Line B"]


def test_visible_some_lines_hidden_by_missing_flag():
    """visible filters out lines whose condition requires a flag not in the current state."""
    state, _ = walker.initial()
    # Initial state has no flags. This condition requires 'needs_key'.
    cond = {"all": ["needs_key"], "none": [], "min": {}, "max": {}}
    lines = [
        (cond, "Hidden Line"),
        (None, "Visible Line"),
    ]
    result = walker.visible(lines, state)
    assert result == ["Visible Line"]


def test_visible_empty_lines_returns_empty_list():
    """visible returns an empty list when given no lines."""
    state, _ = walker.initial()
    result = walker.visible([], state)
    assert result == []
