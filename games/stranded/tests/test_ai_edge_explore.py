"""Tests for edge cases in explore.py."""

import explore
import story
import walker


def test_search_limit_zero_returns_only_start():
    """search with limit=0 returns only the start state without iterating."""
    result = explore.search(limit=0)
    assert len(result["order"]) == 1
    start, _ = walker.initial()
    assert result["order"][0] == start


def test_search_empty_allowed_set_stops_at_start():
    """search with an empty allowed set cannot traverse any edges."""
    result = explore.search(allowed=set())
    assert len(result["order"]) == 1
    start, _ = walker.initial()
    assert result["order"][0] == start


def test_peek_need_zero_opens_immediately():
    """peek with need=0 opens immediately regardless of tried choices."""
    result = explore.search()
    for state in result["order"]:
        scene = story.SCENES[state[0]]
        if len(scene["choices"]) > 0:
            peek_result = explore.peek(state, set(), need=0)
            assert peek_result["open"] is True
            return
    assert False, "No scene with choices found"


def test_peek_need_exceeds_choices():
    """peek returns correct remaining need when need exceeds number of choices."""
    result = explore.search()
    for state in result["order"]:
        scene = story.SCENES[state[0]]
        if len(scene["choices"]) > 0:
            num_choices = len(scene["choices"])
            peek_result = explore.peek(state, set(), need=num_choices + 5)
            assert peek_result["open"] is False
            assert peek_result["need"] == num_choices + 5
            return
    assert False, "No scene with choices found"


def test_route_to_empty_taken_returns_none_for_non_start():
    """route_to with an empty taken set cannot reach any non-start scene."""
    start_scene, _ = walker.initial()
    result = explore.search()
    for state in result["order"]:
        if state[0] != start_scene:
            target = state[0]
            path = explore.route_to(set(), target)
            assert not path
            return
    assert False, "Could not find a non-start scene"


def test_loose_end_all_edges_taken_returns_none():
    """loose_end returns None when every reachable edge has been tried."""
    result = explore.search()
    taken = set()
    for state in result["order"]:
        scene = story.SCENES[state[0]]
        for i in range(len(scene["choices"])):
            ok, _ = walker.available(state, i)
            if ok:
                taken.add((state[0], i, walker.destination(state, i)))
    end_result = explore.loose_end(taken, "")
    assert end_result is None
