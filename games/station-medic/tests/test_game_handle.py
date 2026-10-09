"""The engine's single entry point: actions in, the whole view out; the save contract."""

import json

import game
import progress


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()
    return call(action="open")


def test_open_shows_the_first_shift_with_everything_the_page_draws():
    v = fresh()
    assert v["shift"]["id"] == "1-1" and v["patients"] and v["sheet"] and v["cabinet"]["items"]
    assert v["totals"]["done"] == 0 and v["rooms"][0]["open"] and not v["rooms"][1]["open"]
    assert "portrait" in v["patients"][0] and v["about"]["notice"]


def test_a_cure_finishes_the_shift_clean_and_records_it():
    fresh()
    v = call(action="treat", p=0, x=0)
    assert v["ok"] and v["result"]["grade_name"] == "Clean" and v["totals"]["clean"] == 1
    assert v["tally"]["treats"] == 1 and "hollow" in game.get_state()["cured"]


def test_a_refused_action_changes_nothing_and_says_why():
    fresh()
    v = call(action="scan", p=0, t=0)
    assert not v["ok"] and v["message"] and v["tally"]["scans"] == 0
    assert call(action="treat", p=7, x=0)["ok"] is False
    assert call(action="treat", p=True, x=0)["ok"] is False
    assert "error" in json.loads(game.handle("not json")) and "error" in call(action="nope")


def test_restore_is_free_keeps_seals_and_counts_in_the_tally():
    fresh()
    call(action="treat", p=0, x=0)
    v = call(action="restore")
    assert v["result"] is None and v["totals"]["clean"] == 1 and v["tally"]["restores"] == 1
    assert v["patients"][0]["closed"] is False


def test_a_wrong_call_costs_a_seal_never_a_dead_end():
    fresh()
    call(action="pick", shift="1-1")
    v = call(action="comfort", p=0)
    assert v["result"]["grade_name"] == "Steady" and v["shift"]["cost"] == 1
    call(action="restore")
    v = call(action="treat", p=0, x=0)
    assert v["result"]["best_name"] == "Clean"         # seals only rise


def test_borrowing_adds_one_and_costs_one_so_a_short_shelf_is_never_a_dead_end():
    fresh()
    v = call(action="borrow", item=0)
    assert v["shift"]["cost"] == 1 and v["cabinet"]["items"][0]["count"] == 2 and v["tally"]["borrows"] == 1


def test_chapters_gate_and_next_goes_to_an_open_undone_shift():
    fresh()
    assert not call(action="pick", shift="2-1")["ok"]
    for sid in progress.CHAPTERS[0]["shifts"][:5]:
        game.game.best[sid] = 3
    assert call(action="pick", shift="2-1")["ok"]
    assert call(action="next")["shift"]["id"] != "2-1"


def test_an_unfinished_shift_keeps_its_actions_when_you_leave_and_come_back():
    fresh()
    call(action="pick", shift="1-2")
    call(action="treat", p=0, x=0)
    call(action="pick", shift="1-1")
    v = call(action="pick", shift="1-2")
    assert v["patients"][0]["closed"] and not v["patients"][1]["closed"]


def test_hint_ladder_climbs_three_rungs_and_the_answer_can_be_done():
    fresh()
    for sid in progress.CHAPTERS[0]["shifts"][:5]:
        game.game.best[sid] = 3
    call(action="pick", shift="2-1")
    assert call(action="hint")["hint"]["nudge"]
    assert call(action="hint")["hint"]["hint"]
    v = call(action="hint")
    assert v["hint"]["answer"] and not call(action="hint")["ok"]
    v = call(action="hint_do")
    assert v["ok"] and v["tally"]["scans"] == 1 and v["tally"]["hints"] == 3
    assert call(action="hint_do")["ok"] is False


def test_following_the_hints_all_the_way_finishes_every_shift_clean():
    for d in progress.DATA.values():
        fresh()
        game.game.best = {sid: 3 for sid in progress.ORDER}
        game.game._enter(d["id"])
        for _ in range(60):
            if game.game.case.done(game.game.st):
                break
            for _r in range(3):
                call(action="hint")
            v = call(action="hint_do")
            assert v["ok"], (d["id"], v["message"])
        assert game.game.result["grade"] == 3, d["id"]


def test_save_round_trip_and_tampering():
    fresh()
    call(action="treat", p=0, x=0)
    call(action="pick", shift="1-2")
    call(action="treat", p=1, x=0)
    state = game.get_state()
    json.dumps(state)
    assert state["best"] == {"1-1": 3} and state["run"] == {"1-2": ["treat:1:0"]} and state["cur"] == "1-2"
    game.game.__init__()
    game.load_state(json.loads(json.dumps(state)))
    v = call(action="open")
    assert v["shift"]["id"] == "1-2" and v["patients"][1]["closed"] and v["totals"]["clean"] == 1
    for bad in (None, 5, "x", [], {"best": {"1-1": 9, "zz": 3}, "run": {"1-2": ["scan:0:0"]}, "cur": "2-8", "tally": {"scans": -4, "treats": True},
                                   "cured": "x", "flags": [1], "tests": ["nope"]}):
        game.game.__init__()
        game.load_state(bad)
        v = call(action="open")
        assert v["shift"]["id"] == "1-1" and v["totals"]["done"] == 0 and v["tally"]["scans"] == 0 and v["tally"]["treats"] == 0


def test_a_fresh_game_saves_nothing_and_new_keys_appear_only_when_not_default():
    fresh()
    assert game.get_state() == {}
    call(action="hint")
    assert game.get_state() == {"tally": {"hints": 1}}


def test_reset_starts_over():
    fresh()
    call(action="treat", p=0, x=0)
    v = call(action="reset")
    assert v["totals"]["done"] == 0 and v["tally"]["treats"] == 0 and game.get_state() == {}
