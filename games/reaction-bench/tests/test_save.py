"""The save contract: get_state() writes only what differs from a fresh game; load_state() validates every field on its own."""

import copy
import json

import game
import reactions
from .helpers import call, solve, open_chapter


def fresh():
    game.game.__init__()


def test_a_fresh_game_saves_as_just_its_layout_version():
    assert game.get_state() == {"schema": 1} and game.SCHEMA == 1


def test_only_changed_keys_are_written_and_the_state_is_json_safe():
    solve("carbon-dioxide")
    call(action="pick", reaction="water")
    call(action="dial", index=0, value=3)
    state = game.get_state()
    assert set(state) == {"schema", "cur", "shelf", "dials", "tally", "achievements_earned"}
    assert state["shelf"] == {"carbon-dioxide": 1} and state["dials"] == {"water": [3, 1, 1]} and state["cur"] == "water"
    assert state["tally"] == {"turns": 1, "runs": 1}                       # carbon dioxide needs no turn; the water dial was turned once
    assert json.loads(json.dumps(state)) == state


def test_round_trip_keeps_the_whole_game():
    open_chapter(1)
    call(action="pick", reaction="methane")
    call(action="choose", option=0)
    call(action="choose", option=2)
    call(action="dial", index=1, value=2)
    call(action="pick", reaction="propane")
    call(action="choose", option=3)
    before = game.get_state()
    view_before = call(action="open")
    fresh()
    game.load_state(json.loads(json.dumps(before)))
    assert game.get_state() == before
    after = call(action="open")
    assert after["tally"] == view_before["tally"] and after["reaction"]["choices"] == view_before["reaction"]["choices"] == after["reaction"]["choices"]
    call(action="pick", reaction="methane")
    assert call(action="open")["reaction"]["species"][1]["coef"] == 2


def test_a_picked_round_survives_a_reload_with_its_dials_open_and_first_flag():
    open_chapter(1)
    call(action="pick", reaction="ethanol")
    call(action="choose", option=2)
    state = game.get_state()
    assert state["picked"] == ["ethanol"] and state["first"] == ["ethanol"]
    fresh()
    game.load_state(state)
    assert call(action="open")["reaction"]["picked"] and call(action="dial", index=0, value=2)["ok"]


def test_wrong_tries_are_saved_for_unpicked_rounds_only():
    open_chapter(1)
    call(action="pick", reaction="ethanol")
    call(action="choose", option=0)
    assert game.get_state()["tried"] == {"ethanol": [0]}
    call(action="choose", option=2)
    assert "tried" not in game.get_state()


def test_load_validates_every_field_alone():
    solve("water")
    good = game.get_state()
    for key, bad in (("cur", 7), ("cur", "no-such"), ("shelf", [1]), ("shelf", {"water": "x"}), ("dials", {"water": [1]}), ("dials", {"water": [0, 1, 1]}),
                     ("dials", {"water": [13, 1, 1]}), ("dials", {"water": [True, 1, 1]}), ("tally", {"turns": -3}), ("tally", [1]), ("picked", "x"),
                     ("tried", {"methane": [9]}), ("first", {"x": 1})):
        data = copy.deepcopy(good)
        data[key] = bad
        fresh()
        game.load_state(data)                                              # never raises
        v = call(action="open")
        assert v["reaction"]["id"] in reactions.BY_ID, key
        if key not in ("shelf", "cur"):
            assert v["totals"]["shelved"] == 1, key                        # the good fields survive a bad neighbour


def test_a_hand_edited_save_cannot_skip_a_closed_chapter():
    data = {"schema": 1, "shelf": {"methane": 3, "limestone": 1, "water": 2}, "cur": "limestone", "picked": ["methane"], "dials": {"methane": [1, 2, 1, 2]}}
    game.load_state(data)
    v = call(action="open")
    assert v["totals"]["shelved"] == 1 and v["reaction"]["id"] == "carbon-dioxide"        # only water counts
    assert game.get_state() == {"schema": 1, "shelf": {"water": 2}, "achievements_earned": ["first_balance"]}


def test_a_shelved_round_is_always_loaded_as_picked_and_a_save_with_a_gap_is_judged_in_order():
    ids = [r.id for r in reactions.CHAPTERS[0]["reactions"]][:5]
    data = {"schema": 1, "shelf": dict((i, 1) for i in ids + ["methane"])}
    game.load_state(data)
    v = call(action="pick", reaction="methane")
    assert v["ok"] and v["reaction"]["status"] == "shelved" and v["reaction"]["picked"] and v["reaction"]["choices"] is None


def test_unknown_or_future_layouts_are_not_half_read():
    solve("water")
    for bad in (2, 0, "1", True, None, -1):
        game.load_state({"schema": bad, "shelf": {"water": 1}})
        assert call(action="open")["totals"]["shelved"] == 0, bad
    game.load_state({"shelf": {"water": 1}})                                # a save with no schema is read as layout 1
    assert call(action="open")["totals"]["shelved"] == 1


def test_garbage_saves_load_as_a_fresh_game():
    for junk in (None, [], "x", 5, {"shelf": 3, "tally": "x", "dials": None}):
        game.load_state(junk)
        assert call(action="open")["totals"]["shelved"] == 0


def test_load_clears_what_was_in_progress_and_the_last_run_banner():
    solve("water")
    assert call(action="open")["just"] is not None
    game.load_state({"schema": 1})
    assert call(action="open")["just"] is None and call(action="open")["message"] == ""


def test_dials_equal_to_default_are_not_written():
    call(action="pick", reaction="water")
    call(action="dial", index=0, value=2)
    call(action="dial", index=0, value=1)
    assert "dials" not in game.get_state()
