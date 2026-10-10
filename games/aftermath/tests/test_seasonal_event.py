"""N-2: the first seasonal event end to end (Halloween, "Night of Storms"). The page counts a finished run with
resources left (aftermathRunFinished) and keeps the granted badge list in the save (event_badges)."""

import json
import sys
import types


def _window(**hooks):
    sys.modules["js"].window = types.SimpleNamespace(**hooks)
    return sys.modules["js"].window


def _finish(env):
    while not env.run.is_complete():
        env.resolve_event()


def test_finishing_a_run_tells_the_page_how_many_resources_are_left(game_env):
    seen = []
    _window(aftermathRunFinished=seen.append)
    _finish(game_env)
    assert seen == [game_env.run.resources]


def test_the_hook_fires_once_per_real_run_not_on_a_replay_of_the_same_run(game_env):
    seen = []
    _window(aftermathRunFinished=seen.append)
    m = game_env.module
    while m.run.event_index < len(m.run.schedule) - 1:
        game_env.resolve_event()
    before_last = json.loads(json.dumps(m.get_state()))
    _finish(game_env)
    m.load_state(before_last)
    _finish(game_env)
    assert len(seen) == 1


def test_no_page_hook_is_fine(game_env):
    _window()
    _finish(game_env)
    assert game_env.run.is_complete()


def test_set_event_badges_keeps_only_well_formed_hub_badges(game_env):
    m = game_env.module
    good = {"id": "halloween-2026", "label": "Halloween 2026", "earned_at": "2026-10-31"}
    junk = [good, good, {"id": "Bad_ID", "label": "x"}, {"id": "ok-1", "label": ""}, "text", {"id": "x" * 70, "label": "y"},
            {"id": "ok-2", "label": "Fine", "earned_at": 5}]
    assert m.set_event_badges(json.dumps(junk)) is True
    assert [b["id"] for b in m.event_badges] == ["halloween-2026", "ok-2"]
    assert m.event_badges[1]["earned_at"] == ""
    assert m.set_event_badges("{oops") is False
    assert [b["id"] for b in m.event_badges] == ["halloween-2026", "ok-2"]


def test_badges_ride_the_save_only_when_there_are_some_and_load_back(game_env):
    m = game_env.module
    assert "event_badges" not in m.get_state()
    m.set_event_badges(json.dumps([{"id": "halloween-2026", "label": "Halloween 2026", "earned_at": "2026-10-31"}]))
    state = m.get_state()
    assert state["event_badges"][0]["id"] == "halloween-2026"
    adopted = []
    _window(aftermathAdoptBadges=adopted.append)
    m.event_badges = []
    m.load_state(json.loads(json.dumps(state)))
    assert [b["id"] for b in m.event_badges] == ["halloween-2026"]
    assert json.loads(adopted[0])[0]["id"] == "halloween-2026"


def test_a_save_with_a_tampered_badge_list_loads_without_it(game_env):
    m = game_env.module
    state = m.get_state()
    state["event_badges"] = [{"id": "NOT VALID", "label": "x"}, 5, None]
    m.load_state(state)
    assert m.event_badges == []
