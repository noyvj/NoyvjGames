"""Tests for gen.ready(): checks whether the lazy pack 'practice' (genmake) is loaded."""

import unittest.mock


import gen


def test_ready_returns_true_when_genmake_is_present():
    """Normal case: genmake is in the package, so ready() should be True."""
    assert gen.ready() is True


def test_make_chart_works_when_ready():
    """Normal case: when ready() is True, make_chart returns a chart dict for valid inputs."""
    if gen.ready():
        c = gen.make_chart(1, 0)
        assert c is not None and isinstance(c, dict) and "id" in c


def test_make_chart_returns_none_when_not_ready():
    """Edge case: when ready() is False, make_chart returns None instead of crashing."""
    with unittest.mock.patch.object(gen, "_genmake", return_value=None):
        assert gen.make_chart(1, 0) is None
