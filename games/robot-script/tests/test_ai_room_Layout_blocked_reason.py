import room


def test_blocked_by_wall():
    layout = room.Layout([">.#E"])
    assert layout.blocked_reason(2, 0, 0) == "A wall is in the way."


def test_blocked_by_unlit_door():
    layout = room.Layout([">1AE"])
    assert layout.blocked_reason(2, 0, 0) == "The door is shut. Light switch 1 first."


def test_out_of_bounds_is_an_edge_case():
    layout = room.Layout([">..E"])
    assert layout.blocked_reason(-1, 0, 0) == "That is the edge of the room."
