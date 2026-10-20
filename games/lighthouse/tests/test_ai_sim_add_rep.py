"""Tests for sim.add_rep()."""


import data
import sim


class _MockKeep:
    def __init__(self, rep=50):
        self.reputation = rep
        self.night_stats = {"rep": 0}


def test_add_rep_increases_reputation_within_bounds():
    keep = _MockKeep(rep=40)
    sim.add_rep(keep, 10)
    assert keep.reputation == 50
    assert keep.night_stats["rep"] == 10


def test_add_rep_decreases_reputation_within_bounds():
    keep = _MockKeep(rep=50)
    sim.add_rep(keep, -20)
    assert keep.reputation == 30
    assert keep.night_stats["rep"] == -20


def test_add_rep_caps_at_maximum():
    keep = _MockKeep(rep=data.REP_CAP - 10)
    sim.add_rep(keep, 20)
    assert keep.reputation == data.REP_CAP
    assert keep.night_stats["rep"] == 20
