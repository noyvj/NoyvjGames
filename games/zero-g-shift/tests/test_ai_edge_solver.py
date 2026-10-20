"""Edge-case tests for solver.py: limits, empty inputs, and boundary conditions."""

import pytest
import bays
import rules
import solver


@pytest.fixture(scope="module")
def sample_bay():
    """Use the first bay from the game's data as a valid input source."""
    return bays.BY_ID[bays.ORDER[0]]


@pytest.fixture(scope="module")
def analysis(sample_bay):
    return solver.Analysis(sample_bay)


def test_distance_returns_none_for_unknown_state(analysis, sample_bay):
    """distance() should return None when the state is not in the search graph."""
    unknown_state = (sample_bay.w * sample_bay.h + 10, tuple())
    assert analysis.distance(unknown_state) is None


def test_known_returns_false_for_unknown_state(analysis):
    """known() should return False for states never reached during BFS."""
    unknown_state = (-1, ())
    assert analysis.known(unknown_state) is False


def test_best_move_returns_none_on_cleared_state(sample_bay):
    """best_move() should return None when the state is already cleared."""
    a = solver.Analysis(sample_bay)
    states, _ = rules.replay(sample_bay, sample_bay.line)
    final_state = states[-1]
    assert a.best_move(final_state) is None


def test_line_from_returns_empty_string_on_cleared_state(sample_bay):
    """line_from() should return '' when the state is already cleared."""
    a = solver.Analysis(sample_bay)
    states, _ = rules.replay(sample_bay, sample_bay.line)
    final_state = states[-1]
    assert a.line_from(final_state) == ""


def test_all_optimal_lines_with_zero_limit_returns_empty_list(sample_bay):
    """all_optimal_lines(limit=0) should return an empty list immediately."""
    a = solver.Analysis(sample_bay)
    assert a.all_optimal_lines(limit=0) == []


def test_first_broken_move_with_empty_line_returns_none(sample_bay):
    """first_broken_move() should return None when given an empty line (no moves made)."""
    assert solver.first_broken_move(sample_bay, "") is None
