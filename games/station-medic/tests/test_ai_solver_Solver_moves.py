"""Tests for Solver.moves() in solver.py."""

import cases
from shift import Case
from solver import Solver


COMPILED = [(d, Case(d)) for d in cases.ALL]


def test_moves_returns_actions_in_correct_priority_order():
    """Normal case: moves() concatenates action lists in a specific priority order (treats, steadies, beds, scans)."""
    d, c = COMPILED[0]
    solver = Solver(c)
    st = solver.from_state(c.new_state())
    result = solver.moves(st)

    treats_idx = [i for i, m in enumerate(result) if m[0][0] == "treat"]
    steadies_idx = [i for i, m in enumerate(result) if m[0][0] in ("band", "robot")]
    beds_idx = [i for i, m in enumerate(result) if m[0][0] == "isolate"]
    scans_idx = [i for i, m in enumerate(result) if m[0][0] == "scan"]

    max_treat = max(treats_idx) if treats_idx else -1
    min_steady = min(steadies_idx) if steadies_idx else float('inf')
    max_steady = max(steadies_idx) if steadies_idx else -1
    min_bed = min(beds_idx) if beds_idx else float('inf')
    max_bed = max(beds_idx) if beds_idx else -1
    min_scan = min(scans_idx) if scans_idx else float('inf')

    assert max_treat < min_steady, "Treats should come before steadies"
    assert max_steady < min_bed, "Steadies should come before beds"
    assert max_bed < min_scan, "Beds should come before scans"


def test_moves_returns_steadies_for_shaking_patient():
    """Normal case: a shaking patient without steady flag should generate band or robot moves."""
    target = next((c for _, c in COMPILED if any(p.shaking for p in c.patients)), None)
    assert target is not None, "Expected at least one shift with a shaking patient"
    solver = Solver(target)
    st = solver.from_state(target.new_state())
    result = solver.moves(st)

    steadies = [m for m in result if m[0][0] in ("band", "robot")]
    assert len(steadies) > 0, f"No steadies returned for {target.id}"


def test_moves_returns_empty_list_when_all_patients_closed():
    """Edge case: when every patient is closed, no moves should be generated."""
    d, c = COMPILED[0]
    solver = Solver(c)
    stock = tuple(c.stock0)
    pats = tuple((1, 0, 0, (0,) * len(c.tests), 0, 0) for _ in c.patients)
    st = (stock, pats)
    result = solver.moves(st)
    assert result == []
