import room
from room import Layout


def test_blocked_when_facing_wall():
    layout = Layout([">.#"])
    # Move robot to x=1 facing east so it faces the wall at x=2
    state = (1, 0, 1, -1, 0, 0, 0)
    assert room.cond_holds(layout, state, "blocked") is True


def test_part_on_tile_with_part():
    layout = Layout([">..p"])
    # State with robot at the part's location (x=3)
    state = (3, 0, 1, -1, 1, 0, 0)
    assert room.cond_holds(layout, state, "part") is True


def test_carrying_with_item():
    layout = Layout([">.."])
    # State with robot carrying part index 0
    state = (0, 0, 1, 0, 0, 0, 0)
    assert room.cond_holds(layout, state, "carrying") is True


def test_negated_switch_when_lit():
    layout = Layout([">..1"])
    # State with robot at switch (x=3) and switch lit
    state = (3, 0, 1, -1, 0, 0, 1)
    assert room.cond_holds(layout, state, "!switch") is True
