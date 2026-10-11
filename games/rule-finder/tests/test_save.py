"""The save contract: get_state() writes only what differs from a fresh game; load_state() validates every field on its own."""

import json
import re

import cases
import game
import lang


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def play_a_little():
    fresh()
    call(action="name", rule=lang.rule_json(lang.parse_rule("num", "ge:30")))          # a near miss
    call(action="test", item="12")
    call(action="test", item="7")
    call(action="name", rule=lang.rule_json(lang.parse_rule("num", "even")))
    call(action="pick", case="hinge")
    call(action="test", item="40")


def test_a_fresh_game_saves_as_nothing():
    fresh()
    assert game.get_state() == {}


def test_only_changed_keys_are_written_and_the_state_is_json_safe():
    play_a_little()
    state = game.get_state()
    assert set(state) == {"cur", "named", "log", "tally"}
    assert state["cur"] == "hinge" and state["named"]["latch"]["r"] == "even" and state["named"]["latch"]["m"] == 1
    assert state["tally"] == {"tests": 3, "near": 1}
    assert state["log"]["hinge"] == {"t": ["40"]}
    assert json.loads(json.dumps(state)) == state
    fresh()
    call(action="test", item="12")
    assert set(game.get_state()) == {"log", "tally"} and "cur" not in game.get_state()


def test_the_save_round_trips_exactly():
    play_a_little()
    state = json.loads(json.dumps(game.get_state()))
    before = call(action="open")
    fresh()
    game.load_state(json.loads(json.dumps(state)))
    after = call(action="open")
    before["last"] = None                                   # what was on the gate is not saved
    assert after == before and game.get_state() == state


def test_the_save_holds_nothing_about_time():
    play_a_little()
    assert not re.search(r"time|date|stamp|day|clock", json.dumps(game.get_state()), flags=re.I)


def test_garbage_loads_as_a_fresh_game_and_never_raises():
    for bad in (None, 5, "x", [], {"named": 5, "log": "x", "tally": [], "cur": {}}, {"named": {"latch": 5}}, {"log": {"latch": {"t": 5}}}):
        fresh()
        game.load_state(bad)
        assert game.get_state() == {} and call(action="open")["case"]["id"] == cases.ORDER[0]


def test_every_field_is_checked_on_its_own():
    fresh()
    game.load_state({
        "cur": "nope",
        "named": {"latch": {"t": 3, "r": "even", "m": 1}, "hinge": {"t": -1, "r": "ge:50"}, "pane": {"t": 2, "r": "mult:3"}, "ghost": {"t": 1, "r": "even"},
                  "lever": {"t": 2, "r": "has:7&has:7"}, "spring": {"t": True, "r": "mult:3"}, "rivet": {"t": 99999999, "r": "square"}, "cog": {"t": 1, "r": 5}},
        "log": {"latch": {"t": ["12", 12, "7", "x", "64", 5.5, None, "012"], "f": ["99", "12"]}, "ghost": {"t": ["1"]}, "hinge": "no"},
        "tally": {"tests": 7, "near": -1, "hints": "x"},
    })
    state = game.get_state()
    assert game.game.current == cases.ORDER[0]
    assert set(game.game.named) == {"latch", "lever"}       # a rule that does not agree with the hidden one never counts; an equal one in other words does
    assert state["named"]["latch"] == {"t": 3, "r": "even", "m": 1}
    assert state["log"]["latch"] == {"t": ["12", "7"], "f": ["99"]}          # examples, repeats and junk are dropped
    assert state["tally"] == {"tests": 7}


def test_a_named_case_is_re_judged_by_the_rules_not_trusted():
    fresh()
    game.load_state({"named": {"latch": {"t": 2, "r": "ge:50"}}})
    assert game.game.named == {}
    game.load_state({"named": {"latch": {"t": 2, "r": "~mult:99"}}})
    assert game.game.named == {}
    game.load_state({"named": {"latch": {"t": 2, "r": "even"}, "spring": {"t": 4, "r": "mult:3"}}})
    assert set(game.game.named) == {"latch", "spring"}


def test_loading_a_save_resets_what_was_on_screen():
    play_a_little()
    state = game.get_state()
    call(action="test", item="50")
    game.load_state(state)
    v = call(action="open")
    assert v["last"] is None and v["verdict"] is None and "menu" in v and v["case"]["id"] == "hinge"


def test_a_save_from_a_longer_game_keeps_unknown_cases_out():
    fresh()
    game.load_state({"named": {"some-future-case": {"t": 1, "r": "even"}}, "cur": "some-future-case"})
    assert game.get_state() == {}
