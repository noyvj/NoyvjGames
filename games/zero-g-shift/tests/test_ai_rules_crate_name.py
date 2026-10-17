"""Tests for rules.crate_name()."""

import pytest

import rules


def test_crate_name_returns_circle_for_kind_0():
    """Kind 0 should return the first shape and letter."""
    assert rules.crate_name(0) == "circle crate A"


def test_crate_name_returns_square_for_kind_1():
    """Kind 1 should return the second shape and letter."""
    assert rules.crate_name(1) == "square crate B"


def test_crate_name_returns_diamond_for_kind_3():
    """Kind 3 should return the last shape and letter."""
    assert rules.crate_name(3) == "diamond crate D"


def test_crate_name_raises_index_error_for_out_of_bounds_kind():
    """Passing an index beyond the available kinds should raise IndexError."""
    with pytest.raises(IndexError):
        rules.crate_name(4)
