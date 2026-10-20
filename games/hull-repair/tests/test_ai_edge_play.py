"""Edge-case tests for play.py Drawing class."""


import boards
import play


def test_begin_on_port_accepts_touch():
    """Starting on a valid port should accept the touch and record it in drag."""
    b = boards.ALL_BOARDS[0]
    d = play.Drawing(b)
    port_cell = next(iter(b.port_at.keys()))
    ok, msg = d.begin(port_cell)
    assert ok, msg
    assert msg == ""
    assert d.drag is not None
    assert d.drag["kind"] == "port"


def test_begin_on_invalid_cell_rejects():
    """Starting on a cell that is out of bounds should be rejected."""
    b = boards.ALL_BOARDS[0]
    d = play.Drawing(b)
    invalid_cell = (-1, -1)
    ok, msg = d.begin(invalid_cell)
    assert not ok
    assert msg == "That part of the hull is gone."


def test_move_to_non_adjacent_cell_rejects():
    """Moving to a cell that is not adjacent to the line head should be rejected."""
    b = boards.ALL_BOARDS[0]
    d = play.Drawing(b)
    port_cell = next(iter(b.port_at.keys()))
    d.begin(port_cell)
    invalid_cell = (100, 100)
    ok, msg = d.move(invalid_cell)
    assert not ok
    assert msg == "A line moves one cell at a time."


def test_undo_on_empty_history_returns_false():
    """Calling undo when no history exists should return False and change nothing."""
    b = boards.ALL_BOARDS[0]
    d = play.Drawing(b)
    result = d.undo()
    assert result is False
    assert len(d.history) == 0


def test_clear_on_empty_paths_returns_false():
    """Calling clear when there are no paths should return False and change nothing."""
    b = boards.ALL_BOARDS[0]
    d = play.Drawing(b)
    result = d.clear()
    assert result is False
    assert len(d.paths) == 0
