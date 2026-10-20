"""Tests for market.rank() -- the tuple returned by rank(record) determines the best result per date."""


import market


def test_rank_returns_correct_tuple():
    record = {"stars": 2, "served": 6, "total": 8, "coins": 90}
    r = market.rank(record)
    assert isinstance(r, tuple) and len(r) == 3
    assert r == (2, 6, 90)


def test_rank_comparison_order():
    """Stars > served > coins priority matches merge_record's logic."""
    better = {"stars": 3, "served": 8, "total": 8, "coins": 50}
    worse = {"stars": 2, "served": 9, "total": 8, "coins": 200}
    assert market.rank(better) > market.rank(worse)


def test_rank_equality_for_identical_records():
    rec1 = {"stars": 3, "served": 8, "total": 8, "coins": 150}
    rec2 = {"stars": 3, "served": 8, "total": 8, "coins": 150}
    assert market.rank(rec1) == market.rank(rec2)
