"""Edge-case tests for goals.py."""

import benches
import logbook
import goals


def test_all_goals_empty_inputs():
    """all_goals handles empty cleared and used dicts without error."""
    v = goals.all_goals({}, {})
    assert len(v) == len(goals.GOALS)
    for g in v:
        assert "id" in g and "label" in g and "description" in g
        assert "have" in g and "need" in g and "done" in g
        assert g["have"] == 0
        assert g["need"] > 0
        assert not g["done"]


def test_all_goals_clamps_have_to_need():
    """all_goals ensures have never exceeds need, even if the have function returns a larger value."""
    cleared = {b.id: b.solution_layout() for b in benches.ALL_BENCHES}
    used = {fid for fid, _t, _p, _w in logbook.SHELF}
    v = goals.all_goals(cleared, used)
    for g in v:
        assert g["have"] <= g["need"], f"Goal {g['id']} have={g['have']} exceeded need={g['need']}"


def test_next_goals_count_zero():
    """next_goals returns an empty list when count is 0."""
    v = goals.next_goals({}, {}, count=0)
    assert v == []


def test_next_goals_all_done():
    """next_goals returns an empty list when all goals are already completed."""
    cleared = {b.id: b.solution_layout() for b in benches.ALL_BENCHES}
    used = {fid for fid, _t, _p, _w in logbook.SHELF}
    v = goals.next_goals(cleared, used, count=100)
    assert len(v) == 0


def test_next_goals_preserves_list_order():
    """next_goals returns undone goals in the exact order they appear in GOALS."""
    cleared = {}
    used = {}
    v = goals.next_goals(cleared, used, count=3)
    all_g = goals.all_goals(cleared, used)
    undone_in_order = [g for g in all_g if not g["done"]]
    assert [g["id"] for g in v] == [g["id"] for g in undone_in_order[:3]]


def test_summary_all_done():
    """summary returns correct counts when all goals are completed."""
    cleared = {b.id: b.solution_layout() for b in benches.ALL_BENCHES}
    used = {fid for fid, _t, _p, _w in logbook.SHELF}
    s = goals.summary(cleared, used)
    assert s["done"] == len(goals.GOALS)
    assert s["total"] == len(goals.GOALS)


def test_summary_empty():
    """summary returns zero done and correct total when no benches are cleared."""
    s = goals.summary({}, {})
    assert s["done"] == 0
    assert s["total"] == len(goals.GOALS)
