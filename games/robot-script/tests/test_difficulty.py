"""AN-17: Easy / Normal / Hard. Normal is the game exactly as it always was (pinned below); Easy and Hard change only the help and the
medal bars, Hard keeps its own record of fewest steps, and nothing ever lowers a Normal record or changes what an achievement needs."""

import json

import pytest

import achievements
import dsl
import game
import hints
import progress
import rooms


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")
    game.game.__init__()


LC = "left-at-the-corner"          # par 4 (F F L F); every extra turn is one more harmless step
LC4 = "main: F F L F"
LC5, LC6, LC7, LC8 = (LC4 + " L" * k for k in (1, 2, 3, 4))


def clear_with(rid, text):
    game.game._enter(rid)
    game.game.ed.load(dsl.parse(text))
    return call(action="run")["run"]


def clear_with_ref(rid):
    game.game._enter(rid)
    game.game.ed.load(rooms.BY_ID[rid].ref)
    return call(action="run")["run"]


# ---- Normal is today's game --------------------------------------------------------------------
def script():
    out = []
    for rid in ("wake-up", "long-hall"):
        call(action="pick", room=rid)
        out.append(call(action="hint"))
        out.append(call(action="hint"))
        out.append(call(action="hint"))
        out.append(call(action="load_answer"))
        out.append(call(action="run"))
        out.append(call(action="clear"))
    out.append(call(action="open"))
    return json.dumps(out, sort_keys=True), json.dumps(game.get_state(), sort_keys=True)


def test_normal_is_byte_for_byte_the_same_with_or_without_being_told():
    plain = script()
    game.game.__init__()
    call(action="difficulty", level="normal")
    assert script() == plain


def test_a_detour_through_hard_and_easy_leaves_no_trace():
    plain = script()
    game.game.__init__()
    for level in ("hard", "easy", "normal"):
        call(action="difficulty", level=level)
    assert script() == plain


def test_the_normal_medal_function_is_untouched_for_every_room_and_size():
    for rid in rooms.ORDER:
        par = rooms.BY_ID[rid].par
        assert rooms.limits(par, "normal") == (par, rooms.silver_limit(par))
        for size in range(1, 41):
            assert rooms.medal_for(par, size) == rooms.medal_for(par, size, "normal") == rooms.medal(par, size)
    for bad in ("", None, "extreme"):
        assert rooms.limits(5, bad) == (5, rooms.silver_limit(5))


def test_easy_is_looser_and_hard_is_tighter_for_every_room():
    for rid in rooms.ORDER:
        par = rooms.BY_ID[rid].par
        ng, ns = rooms.limits(par, "normal")
        eg, es = rooms.limits(par, "easy")
        hg, hs = rooms.limits(par, "hard")
        assert (eg, es) == (ng + 2, ns + 2)
        assert hg == ng and ng < hs <= ns
        for size in range(1, 41):
            assert rooms.medal_for(par, size, "easy") >= rooms.medal_for(par, size, "normal") >= rooms.medal_for(par, size, "hard")


def test_normal_hint_ladder_is_unchanged():
    call(action="pick", room="wake-up")
    rungs = [call(action="hint")["hint"] for _ in range(3)]
    assert [h["rung"] for h in rungs] == [1, 2, 3] and rungs[2]["answer"] and rungs[2]["max"] == 3 and rungs[0]["next"] == "Hint"
    assert call(action="hint")["message"] == "That is every rung: the answer is showing."
    assert call(action="load_answer")["ok"]


def test_a_bad_difficulty_is_refused_and_changes_nothing():
    call(action="difficulty", level="hard")
    for bad in ("extreme", "", None, 3, ["easy"], "HARD"):
        v = call(action="difficulty", level=bad)
        assert v["ok"] is False and v["message"] == "That is not a difficulty." and v["difficulty"] == "hard"


def test_the_difficulty_is_never_saved():
    clear_with_ref("wake-up")
    call(action="difficulty", level="hard")
    saved = json.dumps(game.get_state())
    assert "difficulty" not in saved and "hbest" not in saved


# ---- Easy --------------------------------------------------------------------------------------
def test_easy_first_press_opens_the_nudge_and_the_hint_together():
    call(action="difficulty", level="easy")
    call(action="pick", room="wake-up")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["nudge"] and v["hint"]["hint"] and v["hint"]["answer"] is None
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"]
    assert call(action="load_answer")["ok"]
    assert game.game.tally["hints"] == 2


def test_easy_medal_bars_are_two_steps_looser_and_never_change_the_normal_medal():
    r = rooms.BY_ID[LC]                                                           # par 4, Normal silver at 6
    run = clear_with(LC, LC6)                                                     # six steps: Normal silver
    assert run["medal_name"] == "silver"
    call(action="difficulty", level="easy")
    v = call(action="open")
    assert v["room"]["medal_name"] == "gold" and v["room"]["gold"] == r.par + 2 and v["room"]["silver"] == r.silver + 2
    assert v["room"]["best"] == 6
    assert progress.medal_of(game.game.best, LC) == 2                              # the Normal medal did not move
    run = call(action="run")["run"]
    assert run["medal_name"] == "gold" and run["normal_medal_name"] == "silver" and run["difficulty"] == "easy"
    v = call(action="difficulty", level="normal")
    assert v["room"]["medal_name"] == "silver"


def test_easy_totals_and_picker_follow_the_looser_bars_but_clears_stay_the_same():
    clear_with(LC, LC6)
    normal = call(action="open")["totals"]
    easy = call(action="difficulty", level="easy")["totals"]
    assert normal["cleared"] == easy["cleared"] == 1 and normal["gold"] == 0 and easy["gold"] == 1


# ---- Hard --------------------------------------------------------------------------------------
def test_hard_has_no_answer_step():
    call(action="difficulty", level="hard")
    call(action="pick", room="wake-up")
    v = call(action="hint")
    assert v["hint"]["rung"] == 1
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"] and v["hint"]["answer"] is None and v["hint"]["max"] == 2 and v["hint"]["next"] == ""
    v = call(action="hint")
    assert v["ok"] is False and "no answer step" in v["message"] and game.game.rungs["wake-up"] == 2
    editor_before = json.dumps(call(action="open")["program"], sort_keys=True)
    v = call(action="load_answer")
    assert v["ok"] is False and "no answer step" in v["message"] and json.dumps(v["program"], sort_keys=True) == editor_before


def test_hard_hides_the_answer_even_when_normal_already_opened_it():
    call(action="pick", room="wake-up")
    for _ in range(3):
        call(action="hint")
    v = call(action="difficulty", level="hard")
    assert v["hint"]["rung"] == 2 and v["hint"]["answer"] is None and game.game.rungs["wake-up"] == 3
    assert call(action="difficulty", level="normal")["hint"]["answer"]


def test_hard_silver_is_tighter_and_hard_keeps_its_own_record():
    r = rooms.BY_ID[LC]                                                           # par 4: Normal silver at 6, Hard silver at 5
    clear_with(LC, LC6)                                                           # a Normal silver
    v = call(action="difficulty", level="hard")
    assert v["room"]["medal"] == 0 and v["room"]["best"] is None and v["totals"]["cleared"] == 0
    assert v["room"]["silver"] == rooms.limits(r.par, "hard")[1] == 5
    run = call(action="run")["run"]                                               # the same six-step list, now on Hard
    assert run["cleared"] and run["medal_name"] == "bronze" and run["normal_medal_name"] == "silver" and run["new_best"] is True
    assert game.game.hbest == {LC: 6} and game.game.best[LC]["n"] == 6
    run = clear_with(LC, LC5)
    assert run["medal_name"] == "silver" and game.game.hbest[LC] == 5 and game.game.best[LC]["n"] == 5
    run = clear_with_ref(LC)
    assert run["medal_name"] == "gold" and game.game.hbest[LC] == 4
    v = call(action="open")
    assert v["totals"]["gold"] == 1 and [e["medal"] for c in v["rooms"] for e in c["rooms"] if e["id"] == LC] == [3]


def test_a_hard_clear_improves_the_normal_best_and_never_the_other_way_round():
    call(action="difficulty", level="hard")
    clear_with(LC, LC7)
    assert game.game.best[LC]["n"] == 7 and game.game.hbest[LC] == 7
    call(action="difficulty", level="normal")
    clear_with(LC, LC4)
    assert game.game.best[LC]["n"] == 4 and game.game.hbest[LC] == 7                    # Hard has not been played at 4 yet
    call(action="difficulty", level="hard")
    assert call(action="open")["room"]["medal"] == 1                                       # Hard still shows what was cleared on Hard
    clear_with(LC, LC8)
    assert game.game.hbest[LC] == 7 and game.game.best[LC]["n"] == 4                      # a worse list lowers nothing


def test_the_answer_list_earns_no_hard_record_until_the_list_is_cleared():
    call(action="pick", room="wake-up")
    for _ in range(3):
        call(action="hint")
    assert call(action="load_answer")["ok"]
    call(action="difficulty", level="hard")
    run = call(action="run")["run"]
    assert run["cleared"] and run["medal_name"] == "none" and "came from the answer" in run["note"]
    assert game.game.hbest == {} and "wake-up" in game.game.best
    call(action="clear")
    game.game.ed.load(dsl.parse("main: F F F"))
    run = call(action="run")["run"]
    assert run["medal_name"] == "gold" and game.game.hbest["wake-up"] == 3


# ---- achievements and goals follow Normal only ----------------------------------------------------
def test_achievements_and_goals_are_the_same_whatever_the_difficulty():
    for rid in rooms.ORDER:
        clear_with_ref(rid)
    normal = (achievements.earned(game.game.facts()), achievements.goals(game.game.facts(), sandbox=game.game.sandbox_open()))
    game.game.__init__()
    call(action="difficulty", level="hard")
    for rid in rooms.ORDER:
        run = clear_with_ref(rid)
        assert run["medal_name"] == "gold"
    assert (achievements.earned(game.game.facts()), achievements.goals(game.game.facts(), sandbox=game.game.sandbox_open())) == normal
    assert len(game.game.hbest) == 42
    assert call(action="open")["totals"]["gold"] == 42


def test_the_rung_three_achievement_is_still_reachable_on_normal():
    call(action="pick", room="wake-up")
    for _ in range(3):
        call(action="hint")
    assert game.game.facts()["rung3"] == 1


# ---- the save ------------------------------------------------------------------------------------
def test_hard_records_round_trip_through_the_save():
    call(action="difficulty", level="hard")
    clear_with(LC, LC5)
    saved = json.loads(json.dumps(game.get_state()))
    assert saved["hbest"] == {LC: 5}
    game.game.__init__()
    game.load_state(saved)
    assert game.game.hbest == {LC: 5}


@pytest.mark.parametrize("junk", [
    "x", 5, None, [], {LC: "5"}, {LC: True}, {LC: -1}, {LC: 0}, {LC: 99999}, {LC: 2.5},
    {LC: 4}, {"no-such-room": 5}, {"long-hall": 9},
])
def test_a_bad_hard_record_is_dropped_and_the_good_parts_of_the_save_stay(junk):
    game.game.__init__()
    clear_with(LC, LC5)
    saved = json.loads(json.dumps(game.get_state()))
    saved["hbest"] = junk
    game.game.__init__()
    game.load_state(saved)
    assert game.game.best[LC]["n"] == 5
    for rid, n in game.game.hbest.items():
        assert rid in game.game.best and isinstance(n, int) and not isinstance(n, bool) and n >= game.game.best[rid]["n"]


def test_a_hard_record_worse_than_the_normal_best_is_kept():
    clear_with(LC, LC5)
    saved = json.loads(json.dumps(game.get_state()))
    saved["hbest"] = {LC: 7}
    game.game.__init__()
    game.load_state(saved)
    assert game.game.hbest == {LC: 7}


def test_an_old_save_without_a_hard_record_loads_as_before():
    clear_with(LC, LC5)
    saved = json.loads(json.dumps(game.get_state()))
    assert "hbest" not in saved
    game.game.__init__()
    game.load_state(saved)
    assert game.game.hbest == {} and call(action="open")["room"]["best"] == 5


def test_the_sandbox_ignores_the_difficulty():
    for rid in rooms.CHAPTER_LIST[0]["rooms"] + rooms.CHAPTER_LIST[1]["rooms"] + rooms.CHAPTER_LIST[2]["rooms"]:
        clear_with_ref(rid)
    call(action="sandbox")
    for level in ("easy", "normal", "hard"):
        v = call(action="difficulty", level=level)
        assert v["room"]["sandbox"] and v["room"]["medal"] == 0 and v["hint"]["rung"] == 0
    call(action="insert", kind="F")
    assert call(action="run")["run"]["sandbox"] is True


def test_hints_view_limit_is_respected_by_the_helper():
    room = rooms.BY_ID["wake-up"]
    assert hints.view(room, 3)["answer"] and hints.view(room, 3, limit=2)["answer"] is None and hints.view(room, 3, limit=2)["rung"] == 2
