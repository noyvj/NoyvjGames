"""Edge-case tests for optics.py public functions and methods."""

import pytest
import optics


def test_board_empty_rows_rejects():
    """Board rejects an empty list of rows."""
    with pytest.raises(ValueError):
        optics.Board([])


def test_board_jagged_rows_rejects():
    """Board rejects rows that do not form a rectangle."""
    with pytest.raises(ValueError):
        optics.Board(["..", "..."])


def test_board_no_emitter_rejects():
    """Board rejects a layout without an emitter character."""
    with pytest.raises(ValueError):
        optics.Board(["..."])


def test_mirror_out_smallest_and_largest_limits():
    """mirror_out returns valid directions for all documented state and direction limits."""
    for state in (0, 1):
        for d in range(4):
            result = optics.mirror_out(state, d)
            assert isinstance(result, int) and 0 <= result <= 3


def test_prism_out_smallest_and_largest_limits():
    """prism_out returns valid direction/kind pairs for all documented limits."""
    for state in (0, 1):
        for kind in ("W", "S", "L"):
            for d in range(4):
                result = optics.prism_out(state, kind, d)
                assert isinstance(result, list)
                for od, ok in result:
                    assert 0 <= od <= 3 and ok in ("W", "S", "L")


def test_trace_empty_placed_returns_unsolved():
    """trace with an empty placed dict does not light any sensors."""
    b = optics.Board([">o.", "..A"])
    tr = optics.trace(b, {})
    assert not tr.ok
    assert len(tr.lit) == 0


def test_trace_with_halt_stops_beam():
    """trace respects the halt set and lists halted cells in pending."""
    b = optics.Board([">ooA", "...."])
    tr = optics.trace(b, {}, halt=frozenset({(0, 1)}))
    assert not tr.ok
    assert (0, 1) in tr.pending


def test_layout_problem_valid_and_invalid_inputs():
    """layout_problem returns None for valid layouts and a reason string for invalid ones."""
    b = optics.Board([">oo.", "...."])
    tray = {"mirror": 1}

    valid_layout = {(0, 1): ("mirror", 0)}
    assert optics.layout_problem(b, tray, valid_layout) is None

    invalid_piece_layout = {(0, 1): ("laser", 0)}
    reason = optics.layout_problem(b, tray, invalid_piece_layout)
    assert reason is not None and "unknown piece" in reason

    too_many_layout = {(0, 1): ("mirror", 0), (0, 2): ("mirror", 0)}
    reason = optics.layout_problem(b, tray, too_many_layout)
    assert reason is not None and "more mirror pieces" in reason


def test_cell_name_zero_and_large():
    """cell_name formats row and column correctly for zero and large indices."""
    assert optics.cell_name(0, 0) == "row 1, column 1"
    assert optics.cell_name(99, 99) == "row 100, column 100"
