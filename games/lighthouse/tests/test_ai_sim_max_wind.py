"""Tests for max_wind() in sim.py."""

import json
import sys
from pathlib import Path

import game
import sim
from state import Keep

SHARED = Path(__file__).resolve().parent.parent.parent.parent / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))


def req(**kw):
    return json.loads(game.handle(json.dumps(kw)))


from data import CLOCK_BASE, CLOCK_WEIGHTS  # noqa: E402
import unittest.mock as mock  # noqa: E402


def test_max_wind_returns_clock_base_when_no_weights_upgrade():
    """Default max wind is CLOCK_BASE when the keeper has not purchased weights."""
    k = Keep(5)
    sim.to_evening(k)
    assert sim.max_wind(k) == CLOCK_BASE


def test_max_wind_returns_clock_weights_with_upgrade():
    """When the keeper has the weights upgrade, max wind increases to CLOCK_WEIGHTS."""
    k = Keep(5)
    sim.to_evening(k)
    with mock.patch.object(k, "has", return_value=True):
        assert sim.max_wind(k) == CLOCK_WEIGHTS


def test_max_wind_is_a_positive_integer():
    """Edge case: max wind should always be a positive integer suitable for clockwork decay."""
    k = Keep(5)
    sim.to_evening(k)
    result_base = sim.max_wind(k)
    with mock.patch.object(k, "has", return_value=True):
        result_weights = sim.max_wind(k)
    assert isinstance(result_base, int) and result_base > 0
    assert isinstance(result_weights, int) and result_weights > 0
