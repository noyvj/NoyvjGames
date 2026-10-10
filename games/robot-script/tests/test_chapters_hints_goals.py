import json

import achievements
import companion
import dsl
import game
import hints
import progress
import rooms
from solver import shortest


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def clear_with_ref(rid):
    game.game._enter(rid)
    game.game.ed.load(rooms.BY_ID[rid].ref)
    return call(action="run")


def test_compressed_rooms_really_need_the_chapters_idea_for_gold():
    """From chapter 3 on, the reference is shorter than the shortest flat list, and uses the chapter's own tool."""
    tool = {2: {"rep"}, 3: {"call"}, 4: {"until", "if"}}
    for idx in (2, 3, 4):
        for rid in rooms.CHAPTER_LIST[idx]["rooms"]:
            r = rooms.BY_ID[rid]
            flat = shortest(r.layout, limit=2000000)
            assert flat is not None and len(flat) > r.par, rid
            if idx != 3:
                assert dsl.uses(r.ref) & tool[idx], rid
            else:
                assert "call" in dsl.uses(r.ref), rid


def test_the_forty_two_rooms_in_six_chapters():
    assert len(rooms.ORDER) == 42 and [len(c["rooms"]) for c in rooms.CHAPTER_LIST] == [9, 7, 7, 7, 7, 5]
    assert len(companion.PARTS) + len(companion.NEW_PARTS) == 42


def test_toolbox_grows_chapter_by_chapter():
    seen = set()
    for idx, c in enumerate(rooms.CHAPTER_LIST):
        tools = set()
        for rid in c["rooms"]:
            tools |= dsl.allowed_ops(rooms.BY_ID[rid].allow)
        assert seen <= tools or idx == 0
        seen |= tools
    assert {"rep", "A", "B", "until", "if"} <= seen
    assert not (set("LR") & dsl.allowed_ops(rooms.BY_ID["wake-up"].allow))


def test_each_chapter_teaches_with_the_tool_it_adds():
    allowed = {0: "F G P S", 1: "F L R G P S", 2: "F L R G P S rep"}
    for idx, tools in allowed.items():
        for rid in rooms.CHAPTER_LIST[idx]["rooms"]:
            assert set(rooms.BY_ID[rid].allow.split()) == set(tools.split()) or idx == 0, rid


def test_every_chapter_and_room_is_open_from_the_start():
    """AN-5 (owner answer Rs5): no chapter gating, so an empty save can open and play any room."""
    fresh()
    assert all(progress.chapter_open({}, i) for i in range(len(rooms.CHAPTER_LIST)))
    assert all(progress.room_open({}, rid) for rid in rooms.ORDER) and not progress.room_open({}, "no-such-room")
    v = call(action="open")
    for chapter in v["rooms"]:
        assert "open" not in chapter and "need" not in chapter and all("open" not in r for r in chapter["rooms"])
    last = rooms.CHAPTER_LIST[-1]["rooms"][-1]
    v = call(action="pick", room=last)
    assert v["ok"] and v["room"]["id"] == last


def test_old_saves_with_unlock_bookkeeping_still_load():
    """Older saves never stored an unlock, but a save that still carries one (or a cur in a once-locked chapter) must load."""
    fresh()
    game.load_state({"cur": rooms.CHAPTER_LIST[4]["rooms"][2], "unlocked": [1, 2], "chapters_open": 3, "best": {}})
    v = call(action="open")
    assert v["room"]["id"] == rooms.CHAPTER_LIST[4]["rooms"][2]


def test_next_room_offers_the_following_room_across_chapters():
    best = {rid: {"n": 1, "t": ""} for rid in rooms.CHAPTER_LIST[0]["rooms"][:-1]}
    assert progress.next_room(best, rooms.CHAPTER_LIST[0]["rooms"][0]) == rooms.CHAPTER_LIST[0]["rooms"][-1]


def test_the_hint_ladder_climbs_one_rung_at_a_time_and_never_touches_a_medal():
    fresh()
    v = call(action="open")
    assert v["hint"]["rung"] == 0 and v["hint"]["nudge"] == ""
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and v["hint"]["nudge"] and not v["hint"]["hint"]
    assert call(action="load_answer")["ok"] is False
    v = call(action="hint")
    assert v["hint"]["hint"] and "steps" in v["hint"]["hint"] and v["hint"]["answer"] is None
    v = call(action="hint")
    assert v["hint"]["answer"]["text"] == "main: F F F" and v["tally"]["hints"] == 3
    assert call(action="hint")["ok"] is False
    assert call(action="load_answer")["ok"] is True
    run = call(action="run")["run"]
    assert run["medal_name"] == "gold"


def test_hint_text_is_built_from_the_reference():
    r = rooms.BY_ID["stair-haul"]
    assert "1 repeat block" in hints.hint_text(r) and "9 steps" in hints.hint_text(r) and "starts with forward" in hints.hint_text(r)
    assert "plain moves" in hints.hint_text(rooms.BY_ID["wake-up"])


def test_rungs_are_saved_per_room_and_validated():
    fresh()
    call(action="hint")
    state = game.get_state()
    assert state["rungs"] == {"wake-up": 1}
    fresh()
    game.load_state({"rungs": {"wake-up": 9, "nope": 1, "long-hall": 2}})
    assert game.game.rungs == {"long-hall": 2}


def test_scrap_gets_one_part_per_room_and_the_finish_follows_the_medal():
    assert len(companion.PARTS) + len(companion.NEW_PARTS) == len(rooms.ORDER)
    fresh()
    v = clear_with_ref("wake-up")
    assert v["run"]["part"] == {"name": "Left drive roller", "finish": "polished", "first": True}
    assert v["scrap"]["found"] == 1 and v["run"]["scrap_line"]
    game.game.ed.clear()
    call(action="insert", kind="F")
    call(action="insert", kind="F")
    call(action="insert", kind="F")
    again = call(action="run")["run"]
    assert again["part"]["first"] is False


def test_parts_and_zones_views():
    best = {"wake-up": {"n": 3, "t": "main: F F F"}, "long-hall": {"n": 99, "t": "x"}}
    parts = companion.parts_view(best)
    assert parts[0]["found"] and parts[0]["finish"] == "polished"
    assert parts[1]["finish"] == "rusted"
    zones = {z["id"]: z for z in companion.zones_view(parts)}
    assert zones["treads"]["have"] == 2 and zones["treads"]["finish"] == "rusted"
    assert "<svg" in companion.svg(best) and "fin-rusted" in companion.svg(best)


def test_scrap_lines_are_plain_and_deterministic():
    for medal in (1, 2, 3):
        for rid in rooms.ORDER:
            line = companion.line_for(rid, medal)
            assert line and line == companion.line_for(rid, medal) and "—" not in line


def test_goals_show_up_to_three_reachable_ones():
    fresh()
    v = call(action="open")
    ids = [g["id"] for g in v["goals"]]
    assert len(ids) == 3 and ids[0] == "first_light"
    every = [a["id"] for a in achievements.goals({}, count=20)]
    assert "loop_the_loop" in every and "two_minds" in every             # all chapters are open from the start
    assert "tinkerer" not in every and "tinkerer" in [a["id"] for a in achievements.goals({}, count=20, sandbox=True)]


def test_goals_never_list_something_already_earned():
    fresh()
    clear_with_ref("wake-up")
    ids = [g["id"] for g in call(action="open")["goals"]]
    assert "first_light" not in ids


def test_achievement_facts_follow_play():
    fresh()
    clear_with_ref("staircase")
    game.game.ed.clear()
    f = game.game.facts()
    assert f["flag_rep"] == 1 and f["rooms"] == 1 and f["gold"] == 1
    for _ in range(2):
        game.game._enter("wake-up")
        game.game.ed.load(dsl.parse("main: F F F F F F F F"))
        call(action="run")
    assert "comeback" not in game.game.flags
    clear_with_ref("wake-up")
    assert "comeback" in game.game.flags
    assert "first_light" in achievements.earned(game.game.facts())


def test_achievement_list_is_fourteen_with_unique_ids():
    assert len(achievements.ACHIEVEMENTS) == 14 and len(set(achievements.IDS)) == 14
