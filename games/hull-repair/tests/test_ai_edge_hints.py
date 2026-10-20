"""Edge-case tests for hints.py."""

import hints
import boards
import rules


def test_view_clamps_rung_to_limit():
    """view should clamp rung to limit when rung exceeds it."""
    b = boards.BY_ID[boards.ORDER[0]]
    v = hints.view(b, rung=5, limit=2)
    assert v["rung"] == 2
    assert v["max"] == 2


def test_view_handles_zero_rung_and_limit():
    """view with rung=0 and limit=0 should return empty nudge/hint and answer=False."""
    b = boards.BY_ID[boards.ORDER[0]]
    v = hints.view(b, rung=0, limit=0)
    assert v["rung"] == 0
    assert v["nudge"] == ""
    assert v["hint"] == ""
    assert v["answer"] is False


def test_ghosts_clamps_rung_to_limit():
    """ghosts should clamp rung to limit; limit=1 yields no ghosts."""
    b = boards.BY_ID[boards.ORDER[0]]
    g = hints.ghosts(b, rung=10, limit=1)
    assert g == {}


def test_opening_length_limits():
    """opening should respect OPENING and EASY_OPENING constants as upper bounds."""
    b = boards.BY_ID[boards.ORDER[0]]
    _, normal_cells = hints.opening(b, easy=False)
    _, easy_cells = hints.opening(b, easy=True)

    expected_normal = min(len(b.solution[hints.starter(b)]), hints.OPENING + 1)
    expected_easy = min(len(b.solution[hints.starter(b)]), hints.EASY_OPENING + 1)

    assert len(normal_cells) == expected_normal
    assert len(easy_cells) == expected_easy


def test_nudge_text_handles_low_exits():
    """nudge_text should produce different messages based on exit count."""
    b = boards.BY_ID[boards.ORDER[0]]
    text = hints.nudge_text(b)
    # Just ensure it returns a non-empty string and mentions the line name
    assert len(text) > 10
    starter_c = hints.starter(b)
    assert rules.LINE_NAMES[starter_c] in text


def test_starter_returns_valid_line_key():
    """starter should return a line key that exists in the board and has enough length."""
    b = boards.BY_ID[boards.ORDER[0]]
    c = hints.starter(b)
    assert c in b.lines
    assert len(b.solution[c]) >= hints.OPENING
