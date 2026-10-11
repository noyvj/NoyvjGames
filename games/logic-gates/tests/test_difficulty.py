"""AN-17: Easy / Normal / Hard. Normal is the game exactly as it always was (pinned below); Easy and Hard change only the help and
the par bar, keep their own par records, and never lower a Normal record or change what the achievements need."""

import copy
import json

import pytest

import achievements
import game
import levels
import state
from tests.helpers import call, fresh, solve_all


@pytest.fixture(autouse=True)
def back_to_normal():
    call("difficulty", level="normal")
    yield
    call("difficulty", level="normal")


def to_invert():
    fresh()
    call("wire", dest="out:Y", src="in:A")          # level 1 solved: the NOT chip is yours
    return call("start", level="invert")


def solve_invert(extra_chips=0):
    """invert (par 1) with a NOT chip, plus unused chips to go over par."""
    to_invert()
    call("add", type="not")
    for _ in range(extra_chips):
        call("add", type="not")
    call("wire", dest="1.A", src="in:A")
    return call("wire", dest="out:Y", src="1.Y")


# ---- Normal is today's game -------------------------------------------------------------------
SCRIPT = [("wire", dict(dest="out:Y", src="in:A")), ("start", dict(level="invert")), ("hint", {}), ("hint", {}), ("hint", {}),
          ("add", dict(type="not")), ("wire", dict(dest="1.A", src="in:A")), ("wire", dict(dest="out:Y", src="1.Y")),
          ("undo", {}), ("answer", {}), ("hint", {}), ("start", dict(level="both")), ("next", {})]


def run_script(setup):
    fresh()
    setup()
    out = [json.dumps(call(a, **f), sort_keys=True) for a, f in SCRIPT]
    return out, json.dumps(game.get_state(), sort_keys=True)


def test_normal_is_byte_for_byte_the_same_with_or_without_being_told():
    plain = run_script(lambda: None)
    told = run_script(lambda: call("difficulty", level="normal"))
    assert plain == told


def test_going_to_hard_and_back_leaves_no_trace_in_the_save_or_the_views():
    plain = run_script(lambda: None)

    def detour():
        call("difficulty", level="hard")
        call("difficulty", level="easy")
        call("difficulty", level="normal")
    assert run_script(detour) == plain


def test_normal_hint_ladder_pairs_are_unchanged():
    to_invert()
    rungs = []
    for _ in range(3):
        v = call("hint")
        rungs.append((v["hints"]["rung"], bool(v["hints"]["nudge"]), bool(v["hints"]["hint"]), bool(v["hints"]["answer"]), v["hints"]["answer_ready"]))
    assert rungs == [(1, True, False, False, False), (2, True, True, False, False), (3, True, True, True, True)]
    assert call("hint")["note"] == "That is every hint there is."
    v = call("answer")
    assert v["table"]["ok"] and v["hints"]["answer_used"] and v["level"]["record"]["par"] is False
    assert v["hints"]["max"] == 3 and v["difficulty"] == "normal"


def test_normal_asks_for_every_hint_before_the_answer():
    to_invert()
    call("hint")
    call("hint")
    assert call("answer")["note"] == "Ask for the hints first."


def test_normal_undo_depth_is_sixty():
    to_invert()
    for _ in range(8):
        call("add", type="not")
    for _ in range(40):
        call("wire", dest="1.A", src="in:A")
        call("wire", dest="1.A", src="")
    depth = 0
    while call("undo")["can_undo"]:
        depth += 1
    assert state.undo_depth("normal") == 60 and depth + 1 <= 60 and depth + 1 > 12


def test_the_difficulty_is_never_saved_and_a_normal_save_has_no_tiers():
    solve_invert()
    call("difficulty", level="hard")
    data = game.get_state()
    assert "difficulty" not in json.dumps(data) and "tiers" not in json.dumps(data["meta"])


def test_a_bad_difficulty_is_refused_and_changes_nothing():
    call("difficulty", level="hard")
    for bad in ("extreme", "", None, 3, ["easy"], "HARD"):
        v = call("difficulty", level=bad)
        assert v["note"] == "That is not a difficulty." and v["difficulty"] == "hard"
    assert call("difficulty")["difficulty"] == "hard"


def test_changing_the_difficulty_does_not_touch_the_board_or_the_records():
    solve_invert()
    before = json.dumps(game.get_state(), sort_keys=True)
    chips = call("open")["board"]["count"]
    v = call("difficulty", level="hard")
    assert v["board"]["count"] == chips and v["table"]["ok"]
    assert json.dumps(game.get_state(), sort_keys=True) == before


# ---- Easy -------------------------------------------------------------------------------------
def test_easy_first_press_opens_the_nudge_and_the_hint_together():
    to_invert()
    call("difficulty", level="easy")
    v = call("hint")
    assert v["hints"]["rung"] == 2 and v["hints"]["nudge"] and v["hints"]["hint"] and not v["hints"]["answer"]
    v = call("hint")
    assert v["hints"]["rung"] == 3 and v["hints"]["answer"]
    assert call("hint")["note"] == "That is every hint there is."


def test_easy_offers_the_answer_after_one_press_and_it_still_voids_par_everywhere():
    to_invert()
    call("difficulty", level="easy")
    assert call("answer")["note"] == "Ask for the hints first."
    v = call("hint")
    assert v["hints"]["answer_ready"]
    v = call("answer")
    assert v["table"]["ok"] and v["hints"]["answer_used"]
    assert game._rec("invert")["answer"] is True and game._rec("invert")["par"] is False
    assert game.meta["tiers"]["easy"]["invert"]["par"] is False       # the answer voids Easy par too
    call("difficulty", level="normal")
    assert call("open")["level"]["record"]["par"] is False


def test_easy_par_allows_one_chip_over_and_keeps_normal_par_honest():
    solve_invert(extra_chips=0)
    call("difficulty", level="normal")
    assert game._rec("invert")["par"] is True
    fresh()
    call("difficulty", level="easy")
    v = solve_invert(extra_chips=1)                      # two chips: one over the reference
    assert v["table"]["ok"] and v["level"]["record"]["par"] is True
    assert game._rec("invert")["par"] is False           # the Normal record did not move
    assert game.meta["tiers"]["easy"]["invert"] == {"chips": 2, "par": True}
    assert v["stats"]["par"] == 2                         # level 1 (zero chips) and this one
    v = call("difficulty", level="normal")
    assert v["level"]["record"]["par"] is False and v["stats"]["par"] == 1      # Normal: only level 1
    assert state.tier_par(levels.BY_ID["invert"], "easy") == 2 and state.tier_par(levels.BY_ID["invert"], "normal") == 1


def test_easy_two_chips_over_is_not_easy_par():
    fresh()
    call("difficulty", level="easy")
    v = solve_invert(extra_chips=2)
    assert v["table"]["ok"] and v["level"]["record"]["par"] is False
    assert game.meta["tiers"]["easy"]["invert"] == {"chips": 3, "par": False}


def test_easy_shows_a_normal_par_because_it_is_the_stricter_result():
    solve_invert()
    v = call("difficulty", level="easy")
    assert v["level"]["record"]["par"] is True
    assert [i["par"] for ch in v["picker"] for i in ch["levels"] if i["id"] == "invert"] == [True]


# ---- Hard -------------------------------------------------------------------------------------
def test_hard_has_no_answer_step_at_all():
    to_invert()
    call("difficulty", level="hard")
    v = call("hint")
    assert v["hints"]["rung"] == 1
    v = call("hint")
    assert v["hints"]["rung"] == 2 and v["hints"]["hint"] and v["hints"]["answer"] is None and v["hints"]["answer_ready"] is False
    assert v["hints"]["max"] == 2
    assert call("hint")["note"] == "That is every hint there is."
    board = json.dumps(call("open")["board"], sort_keys=True)
    v = call("answer")
    assert "no answer step" in v["note"] and not v["table"]["ok"] and json.dumps(v["board"], sort_keys=True) == board
    assert game._rec("invert")["answer"] is False


def test_hard_hides_the_answer_rung_even_when_normal_already_opened_it():
    to_invert()
    for _ in range(3):
        call("hint")
    v = call("difficulty", level="hard")
    assert v["hints"]["rung"] == 2 and v["hints"]["answer"] is None and v["hints"]["answer_ready"] is False
    assert call("difficulty", level="normal")["hints"]["answer"]


def test_hard_has_fewer_free_undos_but_still_some():
    to_invert()
    call("difficulty", level="hard")
    for _ in range(8):
        call("add", type="not")
    for _ in range(20):
        call("wire", dest="1.A", src="in:A")
        call("wire", dest="1.A", src="")
    depth = 0
    while call("undo")["can_undo"]:
        depth += 1
        assert depth < 100
    assert depth + 1 == state.HARD_UNDO_DEPTH == 12
    # coming back to Hard from Normal trims what is kept
    call("difficulty", level="normal")
    for _ in range(30):
        call("wire", dest="1.A", src="in:A")
        call("wire", dest="1.A", src="")
    call("difficulty", level="hard")
    assert len(game.history) <= 12


def test_hard_par_is_its_own_record_and_a_normal_par_is_not_a_hard_par():
    solve_invert()
    assert game._rec("invert")["par"] is True
    v = call("difficulty", level="hard")
    assert v["level"]["record"]["par"] is False and v["stats"]["par"] == 0
    v = call("open")
    assert v["table"]["ok"]                             # the board is the same, the Hard record is not there yet
    v = call("clear")
    call("add", type="not")
    call("wire", dest="1.A", src="in:A")
    v = call("wire", dest="out:Y", src="1.Y")
    assert v["level"]["record"]["par"] is True and v["stats"]["par"] == 1
    assert game.meta["tiers"]["hard"]["invert"] == {"chips": 1, "par": True}


def test_a_hard_clear_still_counts_as_solved_and_unlocks_the_chip():
    fresh()
    call("difficulty", level="hard")
    v = call("wire", dest="out:Y", src="in:A")
    assert v["table"]["ok"] and v["stats"]["solved"] == 1
    assert [p["type"] for p in call("start", level="invert")["palette"]] == ["not"]


# ---- records never go down, and achievements follow Normal only -------------------------------
def test_a_clear_on_easy_or_hard_never_lowers_a_normal_record():
    solve_invert()
    normal = copy.deepcopy(game.meta["levels"]["invert"])
    for level in ("easy", "hard"):
        call("difficulty", level=level)
        call("clear")
        call("add", type="not")
        call("add", type="not")
        call("add", type="not")
        call("wire", dest="1.A", src="in:A")
        call("wire", dest="out:Y", src="1.Y")
        assert game.meta["levels"]["invert"] == normal
        assert game.meta["levels"]["invert"]["chips"] == 1 and game.meta["levels"]["invert"]["par"] is True


def test_achievements_come_from_normal_records_whatever_the_difficulty():
    fresh()
    solve_all()
    normal_earned = achievements.earned(game.meta)
    normal_goals = achievements.goals(game.meta)
    assert normal_earned
    fresh()
    call("difficulty", level="hard")
    solve_all()
    assert achievements.earned(game.meta) == normal_earned
    assert achievements.goals(game.meta) == normal_goals
    assert all(r["solved"] for r in game.meta["levels"].values())
    assert sum(1 for r in game.meta["tiers"]["hard"].values() if r["par"]) == len(levels.LEVELS)


def test_every_achievement_is_still_reachable_on_normal():
    fresh()
    solve_all()
    assert len(achievements.earned(game.meta)) >= 10


# ---- the save ----------------------------------------------------------------------------------
def test_tier_records_round_trip_through_the_save():
    solve_invert(extra_chips=1)
    call("difficulty", level="easy")
    solve_invert(extra_chips=1)
    saved = json.loads(json.dumps(game.get_state()))
    assert saved["meta"]["tiers"]["easy"]["invert"] == {"chips": 2, "par": True}
    fresh()
    assert game.meta["tiers"]["easy"] == {}
    game.load_state(saved)
    assert game.meta["tiers"]["easy"]["invert"] == {"chips": 2, "par": True}


def test_loading_keeps_the_better_of_each_tier_record():
    mine = state.new_meta()
    mine["tiers"]["hard"]["invert"] = {"chips": 3, "par": False}
    theirs = state.new_meta()
    theirs["tiers"]["hard"]["invert"] = {"chips": 1, "par": True}
    theirs["tiers"]["easy"]["both"] = {"chips": 2, "par": False}
    merged = state.merge_meta(mine, theirs)
    assert merged["tiers"]["hard"]["invert"] == {"chips": 1, "par": True}
    assert merged["tiers"]["easy"]["both"] == {"chips": 2, "par": False}


@pytest.mark.parametrize("junk", [
    "tiers", 5, None, [], {"easy": "x"}, {"easy": []}, {"easy": {"no-such-level": {"chips": 1, "par": True}}},
    {"hard": {"invert": "x"}}, {"hard": {"invert": {"chips": -5, "par": "yes"}}}, {"hard": {"invert": {"chips": float("inf"), "par": 1}}},
    {"hard": {"invert": {"chips": True, "par": True}}}, {"medium": {"invert": {"chips": 1, "par": True}}},
])
def test_a_bad_tiers_blob_never_costs_the_good_parts_of_a_save(junk):
    fresh()
    good = {"schema": 1, "meta": {"levels": {"straight-through": {"solved": True, "chips": 0, "par": True}}, "tiers": junk}}
    game.load_state(good)
    assert game.meta["levels"]["straight-through"]["solved"] is True
    for tier in ("easy", "hard"):
        for rec in game.meta["tiers"][tier].values():
            assert set(rec) == {"chips", "par"} and isinstance(rec["par"], bool)
            assert rec["chips"] is None or (isinstance(rec["chips"], int) and not isinstance(rec["chips"], bool) and 0 <= rec["chips"] <= 500)


def test_an_old_save_without_tiers_loads_as_before():
    fresh()
    game.load_state({"schema": 1, "meta": {"levels": {"straight-through": {"solved": True, "chips": 0, "par": True}}}})
    assert game.meta["tiers"] == {"easy": {}, "hard": {}}
    assert call("open")["stats"]["solved"] == 1


def test_the_sandbox_has_no_hints_or_answer_on_any_difficulty():
    to_invert()
    call("start", level="sandbox")
    for level in ("easy", "normal", "hard"):
        call("difficulty", level=level)
        assert call("open")["hints"] is None
        assert "no hints" in call("hint")["note"]
        assert "no answer" in call("answer")["note"]
