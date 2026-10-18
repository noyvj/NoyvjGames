"""Tests for Case.robots_used() in shift.py."""

import cases
import shift
from shift import Case


def test_robots_used_returns_zero_when_no_patients_are_steadied_by_robot():
    """Normal case: fresh state has no patients steadied by Tally."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()
    assert c.robots_used(st) == 0


def test_robots_used_counts_patients_steadied_by_robot():
    """Normal case: exactly two patients have STEADY=2 (robot-steadied)."""
    d = cases.ALL[0]
    c = Case(d)
    st = list(c.new_state())
    stock, pats, borrowed = st
    new_pats = list(pats)
    count = min(2, len(new_pats))
    for i in range(count):
        pat = list(new_pats[i])
        pat[shift.STEADY] = 2
        new_pats[i] = tuple(pat)
    st = (stock, tuple(new_pats), borrowed)
    assert c.robots_used(st) == count


def test_robots_used_handles_all_patients_steadied_by_robot():
    """Edge case: every patient in the shift is steadied by Tally."""
    d = cases.ALL[0]
    c = Case(d)
    st = list(c.new_state())
    stock, pats, borrowed = st
    new_pats = list(pats)
    for i in range(len(new_pats)):
        pat = list(new_pats[i])
        pat[shift.STEADY] = 2
        new_pats[i] = tuple(pat)
    st = (stock, tuple(new_pats), borrowed)
    assert c.robots_used(st) == len(c.patients)
