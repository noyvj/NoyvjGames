"""Tests for walker.scene_of() function."""


import pytest
import explore
import story
import walker


def test_scene_of_returns_start_scene_for_initial_state():
    """scene_of returns the correct scene dictionary for the initial state."""
    state, _ = walker.initial()
    result = walker.scene_of(state)
    assert result is story.SCENES[walker.START]


def test_scene_of_returns_correct_scene_after_a_step():
    """scene_of returns the scene dictionary corresponding to the state's scene id."""
    result = explore.search()
    for state in result["order"]:
        if result["parent"][state] is not None:
            result_scene = walker.scene_of(state)
            assert result_scene is story.SCENES[state[0]]
            return
    assert False, "Could not find a reachable state"


def test_scene_of_raises_keyerror_for_invalid_scene_id():
    """scene_of raises KeyError when given a state with an unknown scene id."""
    invalid_state = ("nonexistent_scene", (0, 0, 0), ())
    with pytest.raises(KeyError):
        walker.scene_of(invalid_state)
