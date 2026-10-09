import json

import achievements
import companion
import dsl
import game
import progress
import rooms
import sandbox


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def play_all(ids=None):
    """Clear rooms with their reference lists, as a perfect player would."""
    for rid in ids or rooms.ORDER:
        game.game._enter(rid)
        assert game.game.ed.load(rooms.BY_ID[rid].ref)
        run = call(action="run")["run"]
        assert run["cleared"] and run["medal_name"] == "gold", rid


def test_a_perfect_player_clears_every_room_with_gold_and_earns_everything_reachable():
    fresh()
    play_all()
    v = call(action="open")
    assert v["totals"]["cleared"] == 40 and v["totals"]["gold"] == 40 and v["totals"]["chapters_done"] == 6
    assert v["scrap"]["found"] == 40 and v["scrap"]["polished"] == 40
    call(action="sandbox")
    for _ in range(10):
        call(action="insert", kind="F")
        call(action="run")
        call(action="clear")
    for rid in ("wake-up",):
        game.game._enter(rid)
        for _ in range(3):
            call(action="hint")
    done = achievements.earned(game.game.facts())
    missing = [a for a in achievements.IDS if a not in done]
    # the only one needing a halted run first is "Learned From a Bump"
    assert missing == ["learned_from_a_bump"]
    game.game._enter("wake-up")
    game.game.ed.load(dsl.parse("main: F F F F F F F F"))
    call(action="run")
    game.game.ed.load(rooms.BY_ID["wake-up"].ref)
    call(action="run")
    assert set(achievements.earned(game.game.facts())) == set(achievements.IDS)


def test_the_sandbox_is_locked_until_the_last_chapter_is_cleared():
    fresh()
    v = call(action="sandbox")
    assert v["ok"] is False and v["room"]["id"] == "wake-up" and v["sandbox"]["open"] is False
    play_all(rooms.CHAPTER_LIST[5]["rooms"])
    assert progress.sandbox_open(game.game.best)
    v = call(action="sandbox")
    assert v["ok"] and v["room"]["sandbox"] and v["room"]["id"] == "sandbox" and "svg" in v["room"]


def test_sandbox_paint_run_and_tally():
    fresh()
    play_all(rooms.CHAPTER_LIST[5]["rooms"])
    call(action="sandbox")
    v = call(action="sbx_paint", x=2, y=0, tile="#")
    assert v["ok"] and v["room"]["svg"] and v["tally"]["sbx_tiles"] == 1
    assert call(action="sbx_paint", x=2, y=0, tile="#")["tally"]["sbx_tiles"] == 1     # no change, no count
    for k in "FFF":
        call(action="insert", kind=k)
    v = call(action="run")
    assert v["run"]["status"] == "halt" and "wall" in v["run"]["message"] and v["run"]["sandbox"]
    assert v["tally"]["sbx_runs"] == 1 and v["tally"]["runs"] == 5 and v["totals"]["cleared"] == 5
    call(action="clear")
    call(action="insert", kind="R")
    call(action="insert", kind="F")
    v = call(action="run")
    assert v["run"]["status"] in ("short", "cleared") and "column 1, row 2" in v["run"]["message"]


def test_sandbox_refuses_bad_paints_and_keeps_the_robot():
    fresh()
    play_all(rooms.CHAPTER_LIST[5]["rooms"])
    assert call(action="sbx_paint", x=0, y=0, tile="#")["ok"] is False        # nothing open yet: not in the sandbox
    call(action="sandbox")
    assert call(action="sbx_paint", x=0, y=0, tile="#")["ok"] is False        # that is the robot
    assert call(action="sbx_paint", x=9, y=0, tile="#")["ok"] is False
    assert call(action="sbx_paint", x=1, y=1, tile="Z")["ok"] is False
    assert call(action="sbx_paint", x=True, y=0, tile="#")["ok"] is False
    v = call(action="sbx_paint", x=3, y=3, tile="v")
    rows = game.game.sbx_rows
    assert sum(r.count(c) for r in rows for c in "<>^v") == 1 and rows[3][3] == "v" and rows[0][0] == "."
    assert v["room"]["start"] == [3, 3, 2]


def test_sandbox_presets_and_save_round_trip():
    fresh()
    play_all(rooms.CHAPTER_LIST[5]["rooms"])
    call(action="sandbox")
    assert call(action="sbx_preset", name="nope")["ok"] is False
    call(action="sbx_preset", name="maze")
    call(action="insert", kind="rep")
    state = json.loads(json.dumps(game.get_state()))
    assert state["cur"] == "sandbox" and state["sbx"] == sandbox.PRESETS["maze"][1] and state["sdraft"].startswith("main: rep")
    fresh()
    game.load_state(state)
    v = call(action="open")
    assert v["room"]["id"] == "sandbox" and game.game.sbx_rows == sandbox.PRESETS["maze"][1] and v["program"]["size"] == 1


def test_a_save_cannot_open_the_sandbox_early_or_hold_a_bad_room():
    fresh()
    game.load_state({"cur": "sandbox", "sbx": ["x" * 8] * 8, "sdraft": "main: Q"})
    v = call(action="open")
    assert v["room"]["id"] == "wake-up" and game.game.sbx_rows == sandbox.default_rows() and game.game.sbx_prog is None
    for bad in ([">" * 8] * 8, ["........"] * 8, "x", [".......>"] * 7, [">......."] + ["........"] * 6 + [">......."]):
        assert not sandbox.valid_rows(bad)


def test_sandbox_lists_are_not_limited_by_a_room_toolbox():
    fresh()
    play_all(rooms.CHAPTER_LIST[5]["rooms"])
    v = call(action="sandbox")
    assert {p["k"] for p in v["program"]["palette"]} >= {"F", "L", "R", "G", "P", "S", "rep", "until", "if", "callA", "callB"}


def test_goals_after_everything_are_empty_or_reachable():
    fresh()
    play_all()
    call(action="sandbox")
    ids = [g["id"] for g in call(action="open")["goals"]]
    assert ids and all(i not in achievements.earned(game.game.facts()) for i in ids)


def test_every_part_has_a_distinct_name_and_zone_totals_match():
    names = [n for _z, n in companion.PARTS]
    assert len(names) == len(set(names)) == 40
    zones = companion.zones_view(companion.parts_view({}))
    assert sum(z["need"] for z in zones) == 40 and all(z["need"] == n for z, (_i, _n, n) in zip(zones, companion.ZONES))
