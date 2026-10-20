"""Edge-case tests for goals.py in Picture Grid."""

import goals
import pictures


def test_queue_empty_input_returns_initial_goals():
    """Empty solved set and zero cells should yield the first unlock, cell milestone, and finish goals."""
    q = goals.queue(set(), 0)
    not_done = [g for g in q if not g["done"]]
    assert len(not_done) >= 3
    assert not_done[0]["id"] == "open-small-machines"
    assert not_done[1]["id"] == "cells-100"
    assert not_done[2]["id"] == "finish-instruments"


def test_queue_all_solved_and_max_cells_marks_everything_done():
    """When every picture is hung and cells exceed all milestones, every goal must be marked done."""
    all_ids = {p.id for p in pictures.ALL}
    q = goals.queue(all_ids, 10 ** 6)
    assert all(g["done"] for g in q)


def test_queue_clamps_large_cell_count_to_target():
    """Cells far exceeding any milestone target should be clamped by _goal so current never exceeds target."""
    q = goals.queue(set(), 10 ** 9)
    for g in q:
        if g["id"].startswith("cells-"):
            assert g["current"] == g["target"]


def test_queue_gallery_gating_at_open_boundary():
    """Exactly OPEN_AT - 1 hung should leave the unlock goal incomplete; OPEN_AT should complete it."""
    solved_5 = {p.id for p in pictures.GALLERIES[0]["pictures"][:5]}
    q1 = goals.queue(solved_5, 0)
    unlock_goal = next((g for g in q1 if g["id"] == "open-small-machines"), None)
    assert unlock_goal is not None and not unlock_goal["done"]

    solved_6 = {p.id for p in pictures.GALLERIES[0]["pictures"][:6]}
    q2 = goals.queue(solved_6, 0)
    unlock_goal_2 = next((g for g in q2 if g["id"] == "open-small-machines"), None)
    assert unlock_goal_2 is not None and unlock_goal_2["done"]


def test_queue_handles_negative_cells_without_crashing():
    """Negative cell counts should not crash the queue; current will be clamped by min() in _goal."""
    q = goals.queue(set(), -10)
    assert len(q) > 0
    for g in q:
        if g["id"].startswith("cells-"):
            assert g["current"] == -10
