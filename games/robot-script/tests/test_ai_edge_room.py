import room
from room import Layout
import pytest


def test_empty_rows_rejected():
    """An empty list of rows raises LayoutError."""
    with pytest.raises(room.LayoutError):
        Layout([])


def test_max_side_is_accepted():
    """An 8x8 room hits MAX_CELLS exactly (64) and should succeed."""
    rows = ["." * 8] * 8
    rows[0] = "<" + "." * 7
    layout = Layout(rows)
    assert layout.w == 8 and layout.h == 8


def test_max_cells_is_rejected():
    """A room exceeding MAX_CELLS raises LayoutError."""
    with pytest.raises(room.LayoutError):
        Layout(["." * 9] * 8)


def test_initial_state_defaults_are_correct():
    """initial() returns the correct starting tuple for a clean room."""
    layout = Layout([">..E"])
    state = layout.initial()
    assert state == (0, 0, 1, -1, 0, 0, 0)


def test_step_refuses_off_edge_movement():
    """Moving past the room boundary leaves state unchanged and returns a reason."""
    layout = Layout(["<"])
    state = layout.initial()
    new_state, reason = room.step(layout, state, "F")
    assert new_state == state
    assert "edge" in reason.lower()


def test_cond_holds_negated_when_false():
    """A negated condition evaluates correctly when the base condition is false."""
    layout = Layout([">..E"])
    state = layout.initial()
    assert room.cond_holds(layout, state, "!part")
