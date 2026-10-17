"""Tests for Case.beds_used()."""


import cases
import shift
from shift import Case


def _get_case_with_beds():
    """Return a real compiled case that has beds > 0."""
    for d in cases.ALL:
        if int(d.get("beds", 0)) > 0:
            return Case(d)
    return Case(cases.ALL[0])


def test_beds_used_returns_zero_when_no_patients_are_isolated():
    """When no patient is in the cold room, beds_used should be 0."""
    c = _get_case_with_beds()
    st = c.new_state()
    assert c.beds_used(st) == 0


def test_beds_used_counts_only_open_cold_room_patients():
    """Isolated but not yet settled patients count toward beds used."""
    c = _get_case_with_beds()
    st = list(c.new_state())
    pat = list(st[1][0])
    pat[shift.ISO] = 1
    st[1] = (tuple(pat),) + st[1][1:]
    assert c.beds_used(tuple(st)) == 1


def test_beds_used_excludes_closed_patients():
    """A patient who is isolated but already settled (closed) does not count."""
    c = _get_case_with_beds()
    st = list(c.new_state())
    pat = list(st[1][0])
    pat[shift.ISO] = 1
    pat[shift.CLOSED] = 1
    st[1] = (tuple(pat),) + st[1][1:]
    assert c.beds_used(tuple(st)) == 0
