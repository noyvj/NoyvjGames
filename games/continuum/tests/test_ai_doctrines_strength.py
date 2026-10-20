"""Tests for doctrines.strength()."""


import doctrines


def test_strength_returns_one_for_zero_adoptions():
    """A doctrine that has never been adopted is at base strength."""
    assert doctrines.strength(0) == 1.0


def test_strength_returns_one_for_single_adoption():
    """A doctrine adopted in exactly one era is still at base strength."""
    assert doctrines.strength(1) == 1.0


def test_strength_returns_entrenched_factor_for_double_adoption():
    """Once adopted in a second era, the doctrine's strength increases to the entrenched factor."""
    assert doctrines.strength(2) == doctrines.ENTRENCHED_FACTOR


def test_strength_stays_at_entrenched_factor_for_higher_counts():
    """Adopting a doctrine more than twice does not increase its strength further."""
    assert doctrines.strength(5) == doctrines.ENTRENCHED_FACTOR
