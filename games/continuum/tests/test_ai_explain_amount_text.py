"""Tests for explain.amount_text()."""

import explain


def test_positive_int():
    """A positive integer gets a plus sign and no decimal."""
    assert explain.amount_text(5, "int") == "+5"


def test_negative_pct():
    """A negative percentage gets a minus sign, one decimal, and 'points'."""
    assert explain.amount_text(-3.5, "pct") == "−3.5 points"


def test_zero_num():
    """Zero with no unit suffix shows one decimal place and no sign."""
    assert explain.amount_text(0, "num") == "0.0"


def test_edge_case_rounding_to_zero():
    """Values that round to zero should not show a sign prefix."""
    assert explain.amount_text(0.4, "int") == "0"
