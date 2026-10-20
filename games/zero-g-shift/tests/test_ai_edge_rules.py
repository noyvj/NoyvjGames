"""Edge-case tests for rules.py public functions and methods."""


import pytest

import rules


def test_bay_rejects_too_small_grid():
    """Bay.__init__ raises BayError when width or height is less than MIN_SIZE (5)."""
    with pytest.raises(rules.BayError):
        rules.Bay({"id": "too_small", "rows": ["....", "@1A"]})


def test_bay_rejects_too_large_grid():
    """Bay.__init__ raises BayError when width or height exceeds MAX_SIZE (10)."""
    with pytest.raises(rules.BayError):
        rules.Bay({"id": "too_large", "rows": ["@1A" + "....."] * 11})


def test_valid_line_respects_limit_and_rejects_invalid_input():
    """valid_line returns False for non-strings, invalid characters, and lengths exceeding the limit."""
    assert rules.valid_line(123) is False
    assert rules.valid_line("UDLRX") is False
    assert rules.valid_line("U" * 501) is False
    assert rules.valid_line("U" * 500) is True


def test_step_returns_none_on_no_op_move():
    """step returns None when a thrust would not change the player's position or any crate."""
    b = rules.Bay({"id": "wall", "rows": ["#####", "#@1A#", ".....", ".....", "....."]})
    assert rules.step(b, b.start, "U") is None


def test_replay_handles_empty_and_invalid_lines():
    """replay returns None for non-strings and strings with invalid direction characters."""
    b = rules.Bay({"id": "open", "rows": ["#####", "#@1A#", ".....", ".....", "....."]})
    assert rules.replay(b, 123) is None
    assert rules.replay(b, "UDLRX") is None
    assert rules.replay(b, "") == ([b.start], [])


def test_cell_words_handles_boundary_cells():
    """cell_words correctly formats column and row for the smallest (0,0) and largest valid cell indices."""
    b = rules.Bay({"id": "grid", "rows": ["#####", "#@1A#", ".....", ".....", "....."]})
    assert rules.cell_words(b, 0) == "column 1, row 1"
    assert rules.cell_words(b, 24) == "column 5, row 5"
