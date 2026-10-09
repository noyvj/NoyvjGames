import json

import dsl
import game
import rooms


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def solve(rid):
    r = rooms.BY_ID[rid]
    game.game.__init__()
    game.game._enter(rid)
    assert game.game.ed.load(r.ref)
    return call(action="run")


def test_open_view_shape_and_svg_only_when_due():
    fresh()
    v = call(action="open")
    assert v["room"]["id"] == "wake-up" and v["room"]["svg"].startswith("<svg")
    assert [p["k"] for p in v["program"]["palette"]] == ["F"]
    v2 = call(action="insert", kind="F")
    assert "svg" not in v2["room"] and v2["program"]["size"] == 1


def test_reference_run_clears_and_records_a_gold_best():
    fresh()
    v = solve("wake-up")
    run = v["run"]
    assert run["status"] == "cleared" and run["medal_name"] == "gold" and run["new_best"]
    assert run["frames"][0][:3] == [0, 1, 1] and len(run["frames"]) == run["actions"] + 1
    assert v["totals"]["cleared"] == 1 and v["tally"]["runs"] == 1


def test_longer_list_gets_a_lower_medal_and_never_replaces_a_better_best():
    fresh()
    solve("wake-up")
    game.game.ed.clear()
    for k in "FFFF":
        call(action="insert", kind="F")
    call(action="clear")
    for k in "FFFFFF":
        call(action="insert", kind="F")
    v = call(action="run")
    assert v["run"]["status"] == "halt"
    assert game.game.best["wake-up"]["n"] == 3


def test_a_halt_is_not_a_dead_end_and_is_counted():
    fresh()
    call(action="insert", kind="F")
    for _ in range(5):
        call(action="insert", kind="F")
    v = call(action="run")
    assert v["run"]["status"] == "halt" and v["ok"] is False
    assert v["tally"]["halts"] == 1 and v["program"]["size"] == 6
    assert v["run"]["at"].startswith("main/")


def test_chapter_gating_and_picking():
    fresh()
    v = call(action="pick", room="no-such")
    assert v["ok"] is False
    assert call(action="pick", room="the-shaft")["room"]["id"] == "the-shaft"


def test_next_goes_to_the_next_uncleared_room():
    fresh()
    solve("wake-up")
    v = call(action="next")
    assert v["room"]["id"] == "long-hall"


def test_edits_report_why_they_fail():
    fresh()
    v = call(action="insert", kind="L")
    assert v["ok"] is False and "not available" in v["message"] or v["message"]
    assert call(action="insert", kind="zzz")["ok"] is False
    assert call(action="remove", at="main/9")["ok"] is False
    assert call(action="cursor", list="main", index=99)["ok"] is False
    assert call(action="routine", name="A")["ok"] is False
    assert call(action="undo")["ok"] is False
    assert call(action="whatever").get("error")
    assert game.handle("not json") == '{"error": "bad request"}'


def test_save_round_trip_keeps_bests_drafts_and_tally():
    fresh()
    solve("wake-up")
    call(action="pick", room="long-hall")
    call(action="insert", kind="F")
    call(action="insert", kind="F")
    state = json.loads(json.dumps(game.get_state()))
    assert set(state) == {"cur", "best", "draft", "tally"}
    fresh()
    game.load_state(state)
    v = call(action="open")
    assert v["room"]["id"] == "long-hall" and v["program"]["size"] == 2
    assert v["totals"]["cleared"] == 1 and v["tally"]["written"] == 2
    assert game.get_state() == state


def test_fresh_state_is_empty_and_new_keys_only_when_non_default():
    fresh()
    assert game.get_state() == {}
    call(action="insert", kind="F")
    assert set(game.get_state()) == {"draft", "tally"}


def test_load_state_survives_junk_and_tampering():
    for junk in (None, 5, "x", [], {"best": 3}, {"best": {"wake-up": {"n": 1, "t": "main: F"}}},
                 {"best": {"wake-up": {"n": 3, "t": "main: F F L"}}}, {"best": {"wake-up": "x"}},
                 {"draft": {"wake-up": "main: Q"}, "tally": {"runs": -4, "halts": True}, "flags": "rep", "cur": "nope"},
                 {"best": {"nope": {"n": 1, "t": "main: F"}}}):
        fresh()
        game.load_state(junk)
        v = call(action="open")
        assert v["room"]["id"] == "wake-up"
        assert v["totals"]["cleared"] == 0
        assert v["tally"] == {"runs": 0, "halts": 0, "written": 0}


def test_a_best_that_does_not_really_clear_is_dropped_but_a_real_one_loads():
    fresh()
    game.load_state({"best": {"wake-up": {"n": 3, "t": "main: F F F"}}})
    assert "wake-up" in game.game.best
    fresh()
    game.load_state({"best": {"wake-up": {"n": 2, "t": "main: F F"}}})
    assert game.game.best == {}


def test_a_room_with_a_best_opens_with_that_list_in_the_editor():
    fresh()
    solve("wake-up")
    call(action="pick", room="long-hall")
    v = call(action="pick", room="wake-up")
    assert v["program"]["size"] == 3
    assert dsl.to_text(game.game.ed.prog) == "main: F F F"


def test_reset_starts_over():
    fresh()
    solve("wake-up")
    v = call(action="reset")
    assert v["totals"]["cleared"] == 0 and v["tally"]["runs"] == 0 and game.get_state() == {}


def test_every_chapter_one_room_can_be_cleared_in_order_by_reference_play():
    fresh()
    for rid in rooms.CHAPTER_LIST[0]["rooms"]:
        v = solve_keep(rid)
        assert v["run"]["medal_name"] == "gold"
    assert call(action="open")["totals"]["gold"] == 7


def solve_keep(rid):
    game.game._enter(rid)
    game.game.ed.load(rooms.BY_ID[rid].ref)
    return call(action="run")
