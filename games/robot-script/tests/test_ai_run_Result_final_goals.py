import rooms
import run


def test_final_goals_on_cleared_room():
    """When a room is cleared, final_goals() should return all goals with met=True."""
    r = rooms.BY_ID["face-the-pad"]
    result = run.run(r.layout, r.ref)
    assert result.status == "cleared"
    goals = result.final_goals()
    assert isinstance(goals, list) and len(goals) > 0
    for g in goals:
        assert g["met"] is True


def test_final_goals_on_short_run():
    """When a run ends early (short), final_goals() should reflect the actual state."""
    r = rooms.BY_ID["first-switch"]
    partial_prog = {"main": ["F", "F"]}
    result = run.run(r.layout, partial_prog)
    assert result.status == "short"
    goals = result.final_goals()
    assert isinstance(goals, list) and len(goals) > 0
    assert any(not g["met"] for g in goals)


def test_final_goals_matches_result_goals():
    """Edge case: final_goals() should return the same goal state as result.goals."""
    r = rooms.BY_ID["in-order"]
    result = run.run(r.layout, r.ref)
    assert result.final_goals() == result.goals
