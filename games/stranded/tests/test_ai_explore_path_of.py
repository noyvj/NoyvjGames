"""Tests for explore.path_of() function."""

import explore
import walker


def test_path_of_returns_empty_string_for_start_state():
    """path_of returns empty string for the initial state."""
    start, _found = walker.initial()
    result = explore.search()
    assert explore.path_of(result, start) == ""


def test_path_of_returns_correct_path_for_simple_route():
    """path_of returns the correct choice path for a simple route."""
    result = explore.search()
    # Find a state that's one choice away from start
    for state in result["order"]:
        if result["parent"][state] is not None:
            parent_state, choice_idx = result["parent"][state]
            if result["parent"][parent_state] is None:  # Direct child of start
                path = explore.path_of(result, state)
                assert path == str(choice_idx)
                return
    assert False, "Could not find a direct child of start state"


def test_path_of_returns_correct_path_for_multi_step_route():
    """path_of returns the correct choice path for a multi-step route."""
    result = explore.search()
    # Find a state that's two choices away from start
    for state in result["order"]:
        if result["parent"][state] is not None:
            parent_state, _ = result["parent"][state]
            if result["parent"][parent_state] is not None:
                grandparent_state, first_choice = result["parent"][parent_state]
                if result["parent"][grandparent_state] is None:  # Two steps from start
                    second_choice = result["parent"][state][1]
                    path = explore.path_of(result, state)
                    assert path == f"{first_choice}{second_choice}"
                    return
    assert False, "Could not find a state two steps from start"
