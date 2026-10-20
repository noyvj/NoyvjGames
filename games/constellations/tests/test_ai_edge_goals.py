"""Edge-case tests for goals.queue."""


import charts
import goals


def test_queue_with_empty_solved_and_zero_draws():
    """Empty inputs should return a queue starting with unlock and line goals, none done."""
    q = goals.queue({}, 0)
    assert len(q) > 0
    assert all(g["current"] == 0 for g in q if not g["done"])
    # First goal should be opening the next season or a line goal
    assert q[0]["id"].startswith("open-") or q[0]["id"].startswith("lines-")


def test_queue_with_all_charts_solved_and_max_draws():
    """When every chart is solved and draws exceed all steps, all goals should be done."""
    solved = {c: 1 for c in charts.ORDER}
    q = goals.queue(solved, 10000)
    assert all(g["done"] for g in q), "All goals must be marked done when progress exceeds targets"


def test_queue_handles_negative_draws():
    """Negative draws should not crash and should leave line goals undone."""
    q = goals.queue({}, -50)
    lines_goals = [g for g in q if g["id"].startswith("lines-")]
    assert all(not g["done"] for g in lines_goals), "Negative draws should not complete any line goal"


def test_queue_draws_at_exact_step_boundary():
    """Draws exactly matching a step should mark that goal as done."""
    q = goals.queue({}, 50)
    goal_50 = next(g for g in q if g["id"] == "lines-50")
    assert goal_50["done"], "lines-50 should be done when draws equals 50"


def test_queue_ignores_unknown_keys_in_solved():
    """Extra keys in the solved dict should not break the queue generation."""
    solved = {c: 1 for c in charts.ORDER}
    solved["nonexistent_chart"] = 99
    q = goals.queue(solved, 0)
    # Should still generate a valid queue without errors
    assert len(q) > 0
    assert all("id" in g and "done" in g for g in q)
