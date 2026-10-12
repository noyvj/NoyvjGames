"""The save contract: get_state / load_state, every field checked on its own, nothing skippable by editing a save."""

import json

import game as game_module
import missions
import pytest


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.handle(json.dumps({"action": "reset"}))


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def reach(mid):
    do(action="pick", mission=mid)
    m = missions.BY_ID[mid]
    do(action="plan_clear")
    for b in m["ref"]["burns"]:
        do(action="burn_add", **b)
    for body, dv in m["ref"]["pass"].items():
        do(action="pass_set", body=body, dv=dv)
    return do(action="fly")


def test_a_fresh_game_saves_only_the_layout_version():
    assert game_module.get_state() == {"schema": 1}


def test_the_save_is_plain_json_data_with_only_known_keys():
    reach("c1m1")
    do(action="pick", mission="c1m2")
    do(action="burn_add", t=5, head=1.5, dv=0.9)
    do(action="scrub", n=3)
    state = game_module.get_state()
    assert json.loads(json.dumps(state)) == state
    assert set(state) <= {"schema", "cur", "reached", "work", "tally", "achievements_earned"}
    assert state["cur"] == "c1m2" and "c1m1" in state["reached"] and state["work"]["c1m2"]["burns"][0]["head"] == 1.5


def test_round_trip_keeps_progress_plans_and_tally():
    reach("c1m1")
    reach("c1m2")
    do(action="pick", mission="c1m3")
    do(action="burn_add", t=60, head=0, dv=1.04)
    do(action="pass_set", body="moon", dv=-0.16)
    state = json.loads(json.dumps(game_module.get_state()))
    before = do(action="open")
    game_module.handle(json.dumps({"action": "reset"}))
    game_module.load_state(state)
    after = do(action="open")
    assert after["mission"]["id"] == "c1m3" and after["plan"] == before["plan"] and after["totals"]["done"] == 2
    assert after["flight"]["verdict"] == before["flight"]["verdict"] and after["tally"] == before["tally"]
    assert game_module.get_state() == state


def test_a_bad_or_newer_layout_gives_a_fresh_game_and_a_missing_one_is_read_as_layout_one():
    game_module.load_state({"schema": 99, "reached": {"c1m1": {"fuel": 1.0, "flights": 1}}})
    assert game_module.get_state() == {"schema": 1}
    game_module.load_state({"schema": True})
    assert game_module.get_state() == {"schema": 1}
    game_module.load_state({"reached": {"c1m1": {"fuel": 1.0, "flights": 2}}})
    assert game_module.get_state()["reached"]["c1m1"] == {"fuel": 1.0, "flights": 2}


@pytest.mark.parametrize("junk", [None, 5, "x", [], {"reached": 7}, {"reached": {"c1m1": 5}}, {"reached": {"c1m1": {"fuel": "a"}}}, {"work": []}, {"work": {"c1m1": 3}}, {"tally": {"flights": -4}}, {"cur": 12}])
def test_every_field_is_checked_on_its_own_and_junk_never_raises(junk):
    game_module.load_state(junk)
    assert do(action="open")["mission"]["id"] == "c1m1"


def test_a_hand_edited_save_cannot_skip_a_closed_chapter():
    game_module.load_state({"reached": {"c2m1": {"fuel": 3.0, "flights": 1}, "c3m1": {"fuel": 3.0, "flights": 1}}, "cur": "c2m1", "work": {"c2m2": {"burns": [{"t": 1, "dv": 1.0}]}}})
    state = game_module.get_state()
    assert "reached" not in state and "work" not in state and "cur" not in state


def test_saved_plans_are_cleaned_numbers_clamped_unknown_bodies_dropped():
    game_module.load_state({"work": {"c1m1": {"burns": [{"t": 10, "at": "peri", "head": 400, "dv": 1.0}, {"t": 10, "at": "zzz", "head": 1.23456, "dv": 0.12345},
                                                         {"t": -4, "dv": 1}, "x", {"t": 5, "dv": 99}], "pass": {"moon": -0.1234, "pluto": 3, "earth": 1}}}})
    plan = game_module.get_state()["work"]["c1m1"]
    assert plan["burns"] == [{"t": 10, "at": "time", "head": 1.2, "dv": 0.123}]
    assert plan["pass"] == {"moon": -0.123}


def test_a_saved_mission_needs_a_real_fuel_figure_and_is_clamped():
    game_module.load_state({"reached": {"c1m1": {"fuel": 0, "flights": 1}, "c1m2": {"fuel": 1.5, "flights": 0}, "c1m3": {"fuel": 1.5, "flights": 3}}})
    state = game_module.get_state()
    assert list(state["reached"]) == ["c1m2", "c1m3"] and state["reached"]["c1m2"]["flights"] == 1


def test_loading_asks_the_page_to_redraw_only_when_a_page_exists():
    game_module.load_state({})                          # under plain Python there is no js module: it must not raise
