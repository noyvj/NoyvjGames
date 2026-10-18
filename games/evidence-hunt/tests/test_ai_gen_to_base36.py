"""Tests for gen.to_base36()."""

import gen


def test_to_base36_edge_zero():
    """Edge case: zero should return '0'."""
    assert gen.to_base36(0) == "0"


def test_to_base36_normal_small():
    """Normal case: 35 is the last single-digit base-36 character."""
    assert gen.to_base36(35) == "z"


def test_to_base36_normal_boundary():
    """Normal case: 36 rolls over to '10' in base-36."""
    assert gen.to_base36(36) == "10"
