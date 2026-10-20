import room
from room import Layout


def test_all_goals_met_exit_only():
    layout = Layout([">..E"])
    state = (3, 0, 1, -1, 0, 0, 0)
    assert room.goals_met(layout, state) is True


def test_all_goals_met_sockets_and_exit():
    layout = Layout([">poE", "...."])
    # Robot at exit, carrying the part (idx 0), socket filled
    state = (3, 0, 1, 0, 0, 1, 0)
    assert room.goals_met(layout, state) is True


def test_edge_case_no_goals_defined():
    layout = Layout([">..."])
    state = (0, 0, 1, -1, 0, 0, 0)
    assert room.goals_met(layout, state) is False
