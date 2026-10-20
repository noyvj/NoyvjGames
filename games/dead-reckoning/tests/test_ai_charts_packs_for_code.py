"""Tests for charts.packs_for_code()."""


import charts
import gen


def test_invalid_code_returns_empty_list():
    """An unparseable code should yield no packs."""
    assert charts.packs_for_code("invalid-code") == []
    assert charts.packs_for_code("") == []
    assert charts.packs_for_code(None) == []


def test_valid_one_ship_code_returns_practice_pack():
    """A standard practice code needs only the practice generator pack."""
    code = gen.code_of(3, 46655)  # "DR3-ZZZ"
    assert charts.packs_for_code(code) == ["practice"]


def test_valid_two_ship_code_returns_both_packs():
    """A two-ship practice code needs the practice pack and the two-ships pack."""
    # Construct a two-ship code following the DR<d>T-<SEED> format documented in charts.py
    two_ship_code = "DR3T-ZZZ"
    assert charts.packs_for_code(two_ship_code) == ["practice", "two-ships"]
