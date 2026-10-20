"""Edge-case tests for goals.py queue function."""

import goals
import reactions


def test_queue_empty_inputs_returns_initial_goals():
    """Fresh game: empty shelf, zero elements, zero turns."""
    q = goals.queue({}, 0, 0)
    assert len(q) > 0
    assert any(g["id"] == "open-burning" for g in q)
    assert all(g["current"] == 0 for g in q)


def test_queue_clamps_current_when_exceeds_target():
    """Values larger than target should be clamped to target by _goal."""
    huge_turns = 10 ** 9
    full_shelf = {r.id: 1 for r in reactions.ALL}
    q = goals.queue(full_shelf, len(reactions.BENCH_ELEMENTS) + 5, huge_turns)
    for g in q:
        assert g["current"] == g["target"], f"Goal {g['id']} current {g['current']} != target {g['target']}"
        assert g["done"] is True


def test_queue_exact_threshold_values_mark_goals_done():
    """Values exactly matching a milestone threshold should mark the goal done."""
    q = goals.queue({}, 5, 100)
    assert any(g["id"] == "tiles-5" and g["done"] for g in q)
    assert any(g["id"] == "turns-100" and g["done"] for g in q)
    assert all(not g["done"] for g in q if g["id"] == "tiles-10")


def test_queue_partial_shelf_respects_chapter_gating():
    """Goals for closed chapters should not appear, or finish goals match open chapters."""
    shelf = {r.id: 1 for r in reactions.CHAPTERS[0]["reactions"][:4]}
    q = goals.queue(shelf, 0, 0)
    assert any(g["id"] == "open-burning" for g in q)  # Chapter 0 is always open, so this goal appears to track progress
    assert not any(g["id"] == "open-oxides-and-salts" for g in q)  # Chapter 1 is not yet open, so later goals are gated
    assert any(g["id"] == "finish-basics" for g in q)


def test_queue_done_goals_appear_at_end():
    """All completed goals must be appended after pending ones."""
    full_shelf = {r.id: 1 for r in reactions.ALL}
    q = goals.queue(full_shelf, len(reactions.BENCH_ELEMENTS), 2000)
    done_indices = [i for i, g in enumerate(q) if g["done"]]
    todo_indices = [i for i, g in enumerate(q) if not g["done"]]
    if todo_indices:
        assert min(done_indices) > max(todo_indices)
    else:
        assert len(q) == len(done_indices)


def test_queue_handles_negative_values_gracefully():
    """Negative inputs should not crash and current should not exceed target."""
    q = goals.queue({}, -1, -50)
    for g in q:
        assert g["current"] <= g["target"]
        assert g["done"] is False
