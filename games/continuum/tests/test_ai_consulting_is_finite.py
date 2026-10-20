"""Tests for consulting.is_finite()."""

import consulting


def test_is_finite_accepts_normal_integers():
    """Normal integers should be considered finite."""
    assert consulting.is_finite(0) is True
    assert consulting.is_finite(42) is True
    assert consulting.is_finite(-10) is True


def test_is_finite_accepts_normal_floats():
    """Normal floats should be considered finite."""
    assert consulting.is_finite(0.0) is True
    assert consulting.is_finite(3.14) is True
    assert consulting.is_finite(-2.5) is True


def test_is_finite_rejects_nan_and_inf():
    """NaN and infinity should be rejected as non-finite."""
    assert consulting.is_finite(float("nan")) is False
    assert consulting.is_finite(float("inf")) is False
    assert consulting.is_finite(float("-inf")) is False
