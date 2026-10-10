"""The engine's JSON entry point: every action, the save contract (only validated state, only non-default keys), and what the view
may and may not say before the player has earned it."""

import json

import casework as cw
import game
import lexicon as lx
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()
    return call(action="open")


def solve_with_hints():
    for _ in range(80):
        v = call(action="open")
        if v["result"]:
            return v
        call(action="hint")
        call(action="hint")
        call(action="hint")
        v = call(action="hint_do")
    raise AssertionError("did not finish")


def test_the_opening_view_has_everything_the_page_draws():
    v = fresh()
    for key in ("case", "house", "bag", "room", "notebook", "accounts", "could", "sheet", "accuse", "log", "result", "chapters", "totals", "tally", "hint", "about"):
        assert key in v, key
    assert v["case"]["id"] == "1-1" and v["room"] is None and v["bag"]["count"] == 0
    assert v["totals"]["done"] == 0 and len(v["chapters"]) == 5 and v["chapters"][1]["open"] is False


def test_the_view_does_not_say_which_rooms_are_restless_before_you_walk_in():
    v = fresh()
    assert all(r["restless"] is None and not r["tags"] for f in v["house"] for r in f["rooms"])
    assert v["could"] == [] and all(s["fits"] for s in v["sheet"])
    v = call(action="go", room=0)
    rooms = {r["i"]: r for f in v["house"] for r in f["rooms"]}
    assert rooms[0]["entered"] and rooms[0]["restless"] is False and rooms[1]["restless"] is None


def test_walking_packing_reading_and_naming_through_the_handle():
    fresh()
    v = call(action="go", room=2)
    assert v["room"]["restless"] and v["tally"]["rooms"] == 1
    v = call(action="pack", e=1)
    assert v["bag"]["count"] == 1 and v["room"]["uses"][0]["name"] == "EMF reader"
    v = call(action="use", e=1)
    assert v["tally"]["readings"] == 1 and v["notebook"]["rows"][0]["cells"][1]["state"] == cw.POSITIVE
    assert v["bag"]["locked"] and not call(action="pack", e=0)["ok"]
    v = call(action="van")
    assert v["case"]["cost"] == 1 and v["tally"]["trips"] == 1 and v["notebook"]["rows"][0]["cells"][1]["state"] == cw.POSITIVE
    assert not call(action="accuse", kinds=[lx.KIND_INDEX["hushling"]])["ok"], "not on the sheet"
    assert game.game.tally["accusations"] == 0, "a refused name is not an accusation"
    v = call(action="accuse", kinds=[lx.KIND_INDEX["pacer"]])
    assert v["tally"]["wrong"] == 1 and v["case"]["cost"] == 2 and v["case"]["grade_now_name"] == "Steady"
    v = call(action="accuse", kinds=[lx.KIND_INDEX["hearthkeeper"]])
    assert v["result"]["grade_name"] == "Steady" and v["result"]["ending"] and v["totals"]["done"] == 1 and v["case"]["done"]


def test_bad_requests_never_crash_the_engine():
    fresh()
    for req in ({"action": "go", "room": "x"}, {"action": "go", "room": 99}, {"action": "pack"}, {"action": "pack", "e": True}, {"action": "use", "e": 2},
                {"action": "accuse", "kinds": "x"}, {"action": "accuse", "kinds": [1, 2, 3]}, {"action": "accuse", "kinds": [-1]}, {"action": "pick", "case": "9-9"},
                {"action": "pick", "case": "2-1"}, {"action": "hint_do"}, {"action": "return"}):
        v = json.loads(game.handle(json.dumps(req)))
        assert "error" not in v and v["ok"] is False, req
    assert "error" in json.loads(game.handle("not json")) and "error" in json.loads(game.handle("[1]")) and "error" in call(action="nope")


def test_restore_is_free_and_keeps_every_seal():
    fresh()
    solve_with_hints()
    best = dict(game.game.best)
    v = call(action="restore")
    assert v["case"]["cost"] == 0 and v["totals"]["done"] == 1 and game.game.best == best and v["tally"]["restores"] == 1


def test_the_hint_ladder_climbs_one_rung_per_press_and_resets_after_an_action():
    fresh()
    assert call(action="hint")["hint"]["rung"] == 1
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"] and "answer" not in v["hint"]
    assert call(action="hint_do")["ok"] is False, "the answer rung comes first"
    v = call(action="hint")
    assert v["hint"]["answer"] and v["tally"]["hints"] == 3
    assert call(action="hint")["ok"] is False
    v = call(action="hint_do")
    assert v["hint"]["rung"] == 0 and v["tally"]["rooms"] == 1


def test_following_the_hints_finishes_every_case_clean_through_the_handle():
    fresh()
    for cid in progress.ORDER[:6]:
        game.game.best.update({c: 3 for c in progress.ORDER[:5]})
        call(action="pick", case=cid)
        v = solve_with_hints()
        assert v["result"]["grade_name"] == "Clean", cid


def test_the_save_holds_only_what_differs_and_round_trips():
    fresh()
    assert game.get_state() == {}
    call(action="go", room=2)
    call(action="pack", e=1)
    state = game.get_state()
    assert set(state) == {"run", "tally"} and state["run"]["1-1"] == ["go:2", "pack:1"]
    before = game.game.view()
    game.game.__init__()
    game.load_state(json.loads(json.dumps(state)))
    after = game.game.view()
    assert before["house"] == after["house"] and before["bag"] == after["bag"] and before["tally"] == after["tally"]


def test_solved_cases_save_their_best_seal_and_the_guide_facts():
    fresh()
    solve_with_hints()
    state = game.get_state()
    assert state["best"] == {"1-1": 3} and state["met"] == ["hearthkeeper"] and "run" not in state
    assert state["seen"]["hearthkeeper"] and state["eq"] and "ev" in state
    game.game.__init__()
    game.load_state(json.loads(json.dumps(state)))
    assert game.game.best == {"1-1": 3} and game.game.met == ["hearthkeeper"]


def test_a_bad_save_falls_back_field_by_field_and_never_raises():
    garbage = [None, 5, "x", [], {"best": "x"}, {"best": {"1-1": 9, "zz": 3, "1-2": True}}, {"run": {"1-1": ["go:99"]}}, {"run": {"1-1": "nope"}},
               {"cur": "5-8"}, {"cur": 7}, {"tally": {"rooms": -3, "readings": "x"}}, {"met": ["nobody", "glimmer"]}, {"seen": {"glimmer": ["cold", "lights"]}},
               {"kept": ["nothing", "teacup"]}, {"run": {"2-1": ["go:0"]}}]
    for data in garbage:
        game.game.__init__()
        game.load_state(data)
        v = game.game.view()
        assert v["case"]["id"] in progress.DATA
    game.game.__init__()
    game.load_state({"best": {"1-1": 9, "1-2": 2}, "met": ["nobody", "glimmer"], "seen": {"glimmer": ["cold", "lights"]}, "kept": ["nothing", "teacup"], "tally": {"rooms": -3}})
    assert game.game.best == {"1-2": 2} and game.game.met == ["glimmer"] and game.game.seen == {"glimmer": ["lights"]} and game.game.kept == ["teacup"] and game.game.tally["rooms"] == 0
    game.game.__init__()
    game.load_state({"cur": "5-8", "best": {}})
    assert game.game.cur == "1-1", "a locked case cannot be the current one"
    game.load_state({"run": {"1-1": ["go:2", "pack:0", "pack:1", "pack:2", "pack:3"]}})
    assert game.game.tokens == [], "a run that does not replay cleanly is dropped"


def test_every_save_field_is_validated_before_it_is_used():
    game.game.__init__()
    game.load_state({"run": {"1-1": ["go:2", "pack:1"], "1-2": ["pack:9"]}})
    assert game.game.runs == {"1-1": ["go:2", "pack:1"]} and game.game.tokens == ["go:2", "pack:1"]


def test_next_and_pick_walk_between_open_cases_and_keep_unfinished_actions():
    fresh()
    call(action="go", room=0)
    v = call(action="pick", case="1-3")
    assert v["case"]["id"] == "1-3" and game.game.runs["1-1"] == ["go:0"]
    v = call(action="pick", case="1-1")
    assert v["tally"]["rooms"] == 1 and any(r["entered"] for f in v["house"] for r in f["rooms"])
    assert call(action="next")["case"]["id"] == "1-2"


def test_reset_clears_everything():
    fresh()
    solve_with_hints()
    v = call(action="reset")
    assert v["totals"]["done"] == 0 and v["tally"]["rooms"] == 0 and game.get_state() == {}


def test_every_action_moves_a_visible_number():
    fresh()
    v0 = call(action="open")
    v1 = call(action="go", room=0)
    assert v1["tally"]["rooms"] == v0["tally"]["rooms"] + 1
    v2 = call(action="pack", e=0)
    v3 = call(action="use", e=0)
    assert v3["tally"]["readings"] == v2["tally"]["readings"] + 1
    v4 = call(action="van")
    assert v4["tally"]["trips"] == 1
    v5 = call(action="hint")
    assert v5["tally"]["hints"] == 1
    v6 = call(action="accuse", kinds=[lx.KIND_INDEX["pacer"]])
    assert v6["tally"]["accusations"] == 1 and v6["tally"]["wrong"] == 1
    v7 = call(action="restore")
    assert v7["tally"]["restores"] == 1
