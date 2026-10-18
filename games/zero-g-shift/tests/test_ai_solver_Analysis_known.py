"""Tests for Analysis.known() in solver.py."""

import pytest

import bays
import rules
import solver


@pytest.fixture(scope="module")
def analysis():
    return solver.analysis(bays.ALL_BAYS[0])


def test_known_returns_true_for_the_start_state(analysis):
    bay = bays.ALL_BAYS[0]
    assert analysis.known(bay.start) is True


def test_known_returns_true_for_a_reachable_state(analysis):
    bay = bays.ALL_BAYS[0]
    # Replay the first move of the optimal line to get a reachable state
    states, _ = rules.replay(bay, bay.line[:1])
    assert analysis.known(states[-1]) is True


def test_known_returns_false_for_an_unreachable_state(analysis):
    # A state with the player on an out-of-bounds cell index cannot be reached.
    bay = bays.ALL_BAYS[0]
    invalid_state = (bay.w * bay.h, ())
    assert analysis.known(invalid_state) is False
