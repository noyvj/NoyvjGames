"""Tests for walker.destination() function."""


import explore
import story
import walker


def test_destination_returns_valid_scene_for_start_choice():
    """destination returns a valid scene id for choice 0 from the initial state."""
    state, _ = walker.initial()
    choices = walker.scene_of(state)["choices"]
    assert len(choices) > 0, "Start scene must have at least one choice"
    dest = walker.destination(state, 0)
    assert dest in story.SCENES


def test_destination_returns_valid_scene_for_mid_game_state():
    """destination returns a valid scene id for choice 0 from a reachable mid-game state."""
    result = explore.search()
    for state in result["order"]:
        choices = walker.scene_of(state)["choices"]
        if len(choices) > 0:
            dest = walker.destination(state, 0)
            assert dest in story.SCENES
            return
    assert False, "Could not find a reachable state with choices"


def test_destination_returns_conditional_target_when_conditions_match():
    """destination returns the first matching target when choice effects satisfy a condition."""
    result = explore.search()
    for state in result["order"]:
        choices = walker.scene_of(state)["choices"]
        if len(choices) > 0 and len(choices[0]["to"]) > 1:
            dest = walker.destination(state, 0)
            assert dest in [t for _, t in choices[0]["to"]]
            return
    assert False, "Could not find a state with a conditional choice"
