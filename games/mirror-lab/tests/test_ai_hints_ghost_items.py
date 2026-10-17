"""Tests for hints.ghost_items()."""

import benches
import hints


def test_rung_0_returns_empty_list():
    """Rung 0 (nudge only) should not draw any ghosts."""
    bench = benches.BY_ID["c1-1"]
    assert hints.ghost_items(bench, 0) == []


def test_rung_2_returns_first_solution_piece():
    """Rung 2 (hint) should return exactly the first piece the beam needs."""
    bench = benches.BY_ID["c1-1"]
    items = hints.ghost_items(bench, 2)
    assert len(items) == 1
    expected = hints.ordered_solution(bench)[0]
    assert items[0] == expected


def test_rung_3_returns_all_solution_pieces():
    """Rung 3 (answer) should return the full ordered solution."""
    bench = benches.BY_ID["c1-1"]
    items = hints.ghost_items(bench, 3)
    assert len(items) == len(hints.ordered_solution(bench))
    assert items == hints.ordered_solution(bench)


def test_rung_higher_than_3_returns_all_solution_pieces():
    """Rungs beyond the maximum should still return the full solution."""
    bench = benches.BY_ID["c1-1"]
    items = hints.ghost_items(bench, 5)
    assert items == hints.ordered_solution(bench)
