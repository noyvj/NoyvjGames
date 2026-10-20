"""Tests for unease.clamp()."""


import mysteries
import unease


def test_clamp_returns_value_when_within_range():
    cap = mysteries.UNEASE_CAP
    assert unease.clamp(cap // 2) == cap // 2


def test_clamp_returns_zero_for_negative_values():
    assert unease.clamp(-10) == 0
    assert unease.clamp(0) == 0


def test_clamp_returns_cap_for_values_above_cap():
    cap = mysteries.UNEASE_CAP
    assert unease.clamp(cap + 1) == cap
