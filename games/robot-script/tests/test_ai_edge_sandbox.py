import sandbox


def test_valid_rows_rejects_invalid_input():
    """valid_rows should return False for non-lists, wrong dimensions, and unknown characters."""
    assert sandbox.valid_rows(("." * 8,) * 8) is False
    assert sandbox.valid_rows(None) is False
    assert sandbox.valid_rows(["." * 7] * 8) is False
    assert sandbox.valid_rows(["." * 8] * 7) is False
    rows = ["." * 8] * 8
    rows[0] = "Z" + "." * 7
    assert sandbox.valid_rows(rows) is False


def test_valid_rows_requires_single_robot():
    """valid_rows should reject layouts with zero or multiple robots."""
    rows_no_robot = ["." * 8] * 8
    assert sandbox.valid_rows(rows_no_robot) is False
    rows_multi_robot = [">" + "." * 7, "v" + "." * 7] + ["." * 8] * 6
    assert sandbox.valid_rows(rows_multi_robot) is False


def test_paint_rejects_out_of_bounds_and_boolean_coords():
    """paint should refuse coordinates outside the 0-7 range or given as booleans."""
    rows = sandbox.default_rows()
    for x, y in [(-1, 0), (8, 0), (0, -1), (0, 8), (9, 9)]:
        new_rows, changed = sandbox.paint(rows, x, y, "#")
        assert new_rows is rows and changed == "That is outside the room."
    for val in [True, False]:
        new_rows, changed = sandbox.paint(rows, val, 0, "#")
        assert new_rows is rows and changed == "That is outside the room."


def test_paint_refuses_overwriting_robot_without_new_start():
    """paint should refuse to overwrite the robot with a non-start tile."""
    rows = sandbox.default_rows()
    # Robot is at (0, 0) facing east. Try painting it with a wall.
    new_rows, changed = sandbox.paint(rows, 0, 0, "#")
    assert new_rows is rows and changed == "The robot has to be somewhere: place it on another tile first."


def test_paint_moves_robot_when_placing_start_tile():
    """paint should clear the old robot position when placing a new start tile."""
    rows = sandbox.default_rows()
    # Place robot at (1, 0) facing south. Old robot at (0,0) should become "."
    new_rows, changed = sandbox.paint(rows, 1, 0, "v")
    assert changed is True
    assert new_rows[0][0] == "."
    assert new_rows[0][1] == "v"
