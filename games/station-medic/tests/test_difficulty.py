"""AN-17: Easy / Normal / Hard. Normal is the game exactly as it always was (pinned below); Easy and Hard change only the help and the
seal bars (the cost of a shift is the same fact on every difficulty), each keeps its own record, and nothing ever lowers a Normal
seal or changes what an achievement needs."""

import json

import pytest

import achievements
import game
import hints
import progress
import shift as sh

FIRST = progress.ORDER[0]
SECOND = progress.ORDER[1]


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


@pytest.fixture(autouse=True)
def clean():
    game.game.__init__()
    call(action="difficulty", level="normal")
    yield
    call(action="difficulty", level="normal")
    game.game.__init__()


def play(sid, borrows=0):
    """Take a shift from its start with `borrows` spare-supply borrows (cost 1 each), then the careful plan to the end."""
    call(action="pick", shift=sid)
    call(action="restore")
    for _ in range(borrows):
        assert call(action="borrow", item=0)["ok"]
    for _ in range(80):
        if game.game.case.done(game.game.st):
            break
        act = hints.next_action(game.game.case, game.game.st, game.game._solver())
        assert act is not None
        assert game.game.do(act)[0]
    return game.game.result


# ---- Normal is today's game --------------------------------------------------------------------
def script():
    out = [call(action="open")]
    for _ in range(3):
        out.append(call(action="hint"))
    for _ in range(40):
        out.append(call(action="hint_do"))
        if game.game.case.done(game.game.st):
            break
        for _r in range(3):
            out.append(call(action="hint"))
    out.append(call(action="next"))
    out.append(call(action="hint"))
    out.append(call(action="restore"))
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


def test_the_normal_grade_function_is_untouched_for_every_cost():
    for cost in range(0, 60):
        assert sh.grade_for(cost) == sh.grade_for(cost, "normal") == sh.grade_of(cost)
    for bad in ("", None, "extreme"):
        assert sh.grade_for(2, bad) == sh.grade_of(2)


def test_easy_is_looser_and_hard_is_tighter_at_every_cost():
    for cost in range(0, 40):
        assert sh.grade_for(cost, "easy") >= sh.grade_for(cost, "normal") >= sh.grade_for(cost, "hard")
    assert [sh.grade_for(c, "easy") for c in range(5)] == [3, 3, 2, 2, 1]
    assert [sh.grade_for(c, "normal") for c in range(5)] == [3, 2, 2, 1, 1]
    assert [sh.grade_for(c, "hard") for c in range(5)] == [3, 2, 1, 1, 1]


def test_normal_hint_ladder_is_unchanged():
    v = [call(action="hint") for _ in range(3)]
    assert [x["hint"]["rung"] for x in v] == [1, 2, 3] and v[2]["hint"]["answer"] and v[2]["hint"]["max"] == 3
    assert call(action="hint")["message"] == "That is every rung: the answer is showing."
    assert call(action="hint_do")["ok"] is True


def test_a_bad_difficulty_is_refused_and_changes_nothing():
    call(action="difficulty", level="hard")
    for bad in ("extreme", "", None, 3, ["easy"], "HARD"):
        v = call(action="difficulty", level=bad)
        assert v["ok"] is False and v["message"] == "That is not a difficulty." and v["difficulty"] == "hard"


def test_the_difficulty_is_never_saved():
    play(FIRST)
    call(action="difficulty", level="hard")
    saved = json.dumps(game.get_state())
    assert "difficulty" not in saved and "tiers" not in saved


def test_changing_the_difficulty_does_not_touch_the_shift_or_the_seals():
    play(FIRST)
    before = json.dumps(game.get_state(), sort_keys=True)
    for level in ("hard", "easy", "normal"):
        call(action="difficulty", level=level)
    assert json.dumps(game.get_state(), sort_keys=True) == before


# ---- Easy --------------------------------------------------------------------------------------
def test_easy_first_press_opens_the_nudge_and_the_hint_together():
    call(action="difficulty", level="easy")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["nudge"] and v["hint"]["hint"] and "answer" not in v["hint"]
    v = call(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["answer"]
    assert call(action="hint_do")["ok"] and game.game.tally["hints"] == 2


def test_easy_a_cost_of_one_is_clean_and_normal_still_says_steady():
    call(action="difficulty", level="easy")
    r = play(FIRST, borrows=1)
    assert r["cost"] == 1 and r["grade_name"] == "Clean" and r["normal_grade_name"] == "Steady" and r["difficulty"] == "easy"
    assert game.game.best[FIRST] == 2 and game.game.tiers["easy"][FIRST] == 3             # the Normal record is the honest one
    v = call(action="open")
    assert v["shift"]["best_name"] == "Clean" and v["totals"]["clean"] == 1
    v = call(action="difficulty", level="normal")
    assert v["shift"]["best_name"] == "Steady" and v["totals"]["clean"] == 0 and v["totals"]["steady"] == 1


def test_easy_shows_a_normal_clean_seal_and_never_less_than_it():
    play(FIRST)
    v = call(action="difficulty", level="easy")
    assert v["shift"]["best_name"] == "Clean"
    play(SECOND, borrows=3)                                    # Normal rough
    assert game.game.best[SECOND] == 1
    v = call(action="open")
    assert [r["grade_name"] for c in v["rooms"] for r in c["shifts"] if r["id"] == SECOND] == ["Steady"]   # a cost of 3 is Steady on Easy


# ---- Hard --------------------------------------------------------------------------------------
def test_hard_has_no_answer_step():
    call(action="difficulty", level="hard")
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and v["hint"]["max"] == 2
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"] and "answer" not in v["hint"]
    v = call(action="hint")
    assert v["ok"] is False and "no answer step" in v["message"]
    tokens = list(game.game.tokens)
    v = call(action="hint_do")
    assert v["ok"] is False and "no answer step" in v["message"] and game.game.tokens == tokens and not game.game.helped


def test_hard_hides_the_answer_even_when_normal_already_opened_it():
    for _ in range(3):
        call(action="hint")
    v = call(action="difficulty", level="hard")
    assert v["hint"]["rung"] == 2 and "answer" not in v["hint"] and game.game.rung == 3
    assert call(action="difficulty", level="normal")["hint"]["answer"]


def test_hard_seals_are_tighter_and_hard_keeps_its_own_record():
    play(FIRST, borrows=2)                                      # cost 2: a Normal Steady
    assert game.game.best[FIRST] == 2
    v = call(action="difficulty", level="hard")
    assert v["shift"]["best"] == 0 and v["totals"]["done"] == 0
    r = play(FIRST, borrows=2)                                  # the same cost on Hard is Rough
    assert r["grade_name"] == "Rough" and r["normal_grade_name"] == "Steady" and r["new_best"] is True
    assert game.game.tiers["hard"][FIRST] == 1 and game.game.best[FIRST] == 2
    r = play(FIRST, borrows=1)
    assert r["grade_name"] == "Steady" and game.game.tiers["hard"][FIRST] == 2
    r = play(FIRST)
    assert r["grade_name"] == "Clean" and game.game.tiers["hard"][FIRST] == 3 and game.game.best[FIRST] == 3
    v = call(action="open")
    assert v["totals"]["clean"] == 1 and v["shift"]["best_name"] == "Clean"


def test_a_hard_clear_improves_the_normal_seal_and_never_the_other_way_round():
    call(action="difficulty", level="hard")
    play(FIRST, borrows=3)                                      # cost 3: Rough everywhere
    assert game.game.best[FIRST] == 1 and game.game.tiers["hard"][FIRST] == 1
    call(action="difficulty", level="normal")
    play(FIRST)                                                 # a clean Normal shift
    assert game.game.best[FIRST] == 3 and game.game.tiers["hard"][FIRST] == 1             # Hard has not been played clean yet
    call(action="difficulty", level="hard")
    play(FIRST, borrows=3)
    assert game.game.best[FIRST] == 3 and game.game.tiers["hard"][FIRST] == 1


def test_the_answer_step_earns_no_hard_seal_for_that_shift():
    long_one = progress.ORDER[5]                                # 1-6: four careful actions, so the answer step cannot finish it alone
    call(action="pick", shift=long_one)
    for _ in range(3):
        call(action="hint")
    assert call(action="hint_do")["ok"] and not game.game.case.done(game.game.st)   # Normal: the answer step does the next careful action
    call(action="difficulty", level="hard")
    for _ in range(80):
        if game.game.case.done(game.game.st):
            break
        act = hints.next_action(game.game.case, game.game.st, game.game._solver())
        game.game.do(act)
    r = game.game.result
    assert r["grade"] == 3 and "does not count for Hard" in r["note"] and r["new_best"] is False
    assert game.game.tiers["hard"] == {} and game.game.best[long_one] == 3
    r = play(long_one)                                          # restored and played again without the answer step
    assert game.game.tiers["hard"][long_one] == 3 and r["note"] == ""


# ---- achievements follow Normal only --------------------------------------------------------------
def test_achievements_and_goals_are_the_same_whatever_the_difficulty():
    sids = progress.ORDER[:12]
    for sid in sids:
        play(sid)
    normal = (achievements.earned(game.game.facts()), achievements.goals(game.game.facts(), game.game.open_chapters()))
    game.game.__init__()
    call(action="difficulty", level="hard")
    for sid in sids:
        r = play(sid)
        assert r["grade_name"] == "Clean"
    assert (achievements.earned(game.game.facts()), achievements.goals(game.game.facts(), game.game.open_chapters())) == normal
    assert len(game.game.tiers["hard"]) == len(sids)


# ---- the save ------------------------------------------------------------------------------------
def test_tier_seals_round_trip_through_the_save():
    call(action="difficulty", level="hard")
    play(FIRST, borrows=1)
    call(action="difficulty", level="easy")
    play(SECOND, borrows=1)
    saved = json.loads(json.dumps(game.get_state()))
    assert saved["tiers"] == {"easy": {SECOND: 3}, "hard": {FIRST: 2}}
    game.game.__init__()
    game.load_state(saved)
    assert game.game.tiers == {"easy": {SECOND: 3}, "hard": {FIRST: 2}}


@pytest.mark.parametrize("junk", [
    "x", 5, None, [], {"easy": "x"}, {"hard": {FIRST: True}}, {"hard": {FIRST: 4}}, {"hard": {FIRST: 0}}, {"hard": {FIRST: "3"}},
    {"hard": {FIRST: 3}}, {"hard": {"no-such": 2}}, {"hard": {SECOND: 1}}, {"medium": {FIRST: 2}}, {"easy": {SECOND: 2}},
])
def test_a_bad_tier_blob_never_costs_the_good_parts_of_a_save(junk):
    play(FIRST, borrows=2)                                       # Normal steady, so a Hard 3 would be above it
    saved = json.loads(json.dumps(game.get_state()))
    saved["tiers"] = junk
    game.game.__init__()
    game.load_state(saved)
    assert game.game.best[FIRST] == 2
    for tier, recs in game.game.tiers.items():
        for sid, g in recs.items():
            assert sid in game.game.best and g in (1, 2, 3) and (tier == "easy" or g <= game.game.best[sid])


def test_an_old_save_without_tiers_loads_as_before():
    play(FIRST)
    saved = json.loads(json.dumps(game.get_state()))
    assert "tiers" not in saved
    game.game.__init__()
    game.load_state(saved)
    assert game.game.tiers == {"easy": {}, "hard": {}} and call(action="open")["shift"]["best_name"] == "Clean"
