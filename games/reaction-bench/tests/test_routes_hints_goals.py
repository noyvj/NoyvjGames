"""Milestone 4: chapters 4 and 5, the two-step routes, the hint ladder, the three-goals queue and the difficulty levels."""

import json
import re
from pathlib import Path

import pytest

import chem
import game
import goals
import hints
import reactions

from .helpers import call, open_chapter, solve

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
WORKS = reactions.CHAPTERS[4]["reactions"]


@pytest.fixture(autouse=True)
def _level():
    game.difficulty = "normal"
    yield
    game.difficulty = "normal"


def level(name):
    assert call(action="difficulty", level=name)["ok"]


# ---- chapters 4 and 5 and their routes -----------------------------------------------------------------------------------------
def test_chapters_four_and_five_have_the_planned_names_and_every_order_is_a_round():
    assert [c["name"] for c in reactions.CHAPTERS[3:]] == ["Acids, Bases and Swaps", "Works"]
    assert all(r.is_round for c in reactions.CHAPTERS[3:] for r in c["reactions"])
    assert reactions.OPEN_AT == 5 and reactions.chapter_need(3) == 5


def test_the_dial_range_is_still_one_to_twelve_and_every_answer_fits_it():
    assert chem.MIN_COEF == 1 and chem.MAX_COEF == 12
    assert max(c for r in reactions.ALL for c in r.answer) <= 12


def test_there_are_four_routes_of_two_steps_each_in_chapter_five():
    assert sorted(reactions.ROUTES) == ["fertiliser", "iron", "sugar", "sulfuric"]
    for rid, route in reactions.ROUTES.items():
        first, second = route["first"], route["second"]
        assert first.step == 1 and second.step == 2 and first.chapter == second.chapter == 4
        assert second.number == first.number + 1 and second.after == first.id and first.after is None
        assert first.carries in first.products, rid                      # what step one makes ...
        assert first.carries in second.reactants, rid                    # ... step two uses
    assert [r.route for r in WORKS] == [r.route for r in WORKS[::2] for _ in (0, 1)]
    assert not any(r.route for c in reactions.CHAPTERS[:4] for r in c["reactions"])


def test_the_chapter_five_gate_counts_any_five_of_chapter_four():
    shelf = {r.id: 1 for r in reactions.CHAPTERS[3]["reactions"][:4]}
    assert not reactions.chapter_open({**{r.id: 1 for r in reactions.CHAPTERS[2]["reactions"]}, **shelf}, 4)
    shelf[reactions.CHAPTERS[3]["reactions"][7].id] = 1
    assert reactions.chapter_open(shelf, 4)


def test_a_step_two_order_is_locked_until_its_step_one_is_on_the_shelf():
    open_chapter(4)
    v = call(action="pick", reaction="sulfuric-acid")
    assert not v["ok"] and "Sulfur trioxide first" in v["message"] and v["reaction"]["id"] != "sulfuric-acid"
    board = {o["id"]: o for o in call(action="open")["orders"][4]["orders"]}
    assert board["sulfuric-acid"]["locked"] and board["sulfuric-acid"]["needs"] == "Sulfur trioxide" and not board["sulfur-trioxide"]["locked"]
    solve("sulfur-trioxide")
    board = {o["id"]: o for o in call(action="open")["orders"][4]["orders"]}
    assert not board["sulfuric-acid"]["locked"]
    assert call(action="pick", reaction="sulfuric-acid")["ok"]


def test_next_skips_locked_step_two_orders():
    open_chapter(4)
    call(action="pick", reaction="sulfur-trioxide")
    seen = []
    for _ in range(8):
        seen.append(call(action="next")["reaction"]["id"])
    assert "sulfuric-acid" not in seen and "ammonium-phosphate" not in seen and "iron-chloride" not in seen and "sugar-to-fuel" not in seen


def test_the_view_says_what_is_carried_between_the_steps():
    open_chapter(4)
    call(action="pick", reaction="sulfur-trioxide")
    v = call(action="choose", option=1)
    rx = v["reaction"]
    assert rx["route"]["step"] == 1 and rx["route"]["carried"] == "SO3" and "Step 1 of 2" in rx["route"]["note"]
    assert [s.get("carried") for s in rx["species"]] == [None, None, True]
    solve("sulfur-trioxide")
    v = call(action="pick", reaction="sulfuric-acid")
    rx = v["reaction"]
    assert rx["route"]["step"] == 2 and "carried over from Sulfur trioxide" in rx["route"]["note"]
    assert [s.get("carried") for s in rx["species"]] == [True, None]
    assert call(action="pick", reaction="carbon-dioxide")["reaction"]["route"] is None


def test_a_saved_step_two_without_its_step_one_is_not_read():
    ids = {r.id: 1 for c in reactions.CHAPTERS[:3] for r in c["reactions"][:8]}
    ids.update({r.id: 1 for r in reactions.CHAPTERS[3]["reactions"][:5]})
    game.load_state({"schema": 1, "shelf": dict(ids, **{"sulfuric-acid": 2}), "cur": "sulfuric-acid", "dials": {"sulfuric-acid": [2, 1, 1]}})
    v = call(action="open")
    assert "sulfuric-acid" not in game.game.shelf and v["reaction"]["id"] != "sulfuric-acid" and "sulfuric-acid" not in game.get_state().get("dials", {})
    game.load_state({"schema": 1, "shelf": dict(ids, **{"sulfur-trioxide": 1, "sulfuric-acid": 2})})
    assert game.game.shelf["sulfuric-acid"] == 2


def test_every_order_in_chapters_four_and_five_can_be_shelved_in_order():
    for chapter in reactions.CHAPTERS[3:]:
        for r in chapter["reactions"]:
            if not reactions.chapter_open(game.game.shelf, r.chapter):
                open_chapter(r.chapter)
            assert solve(r.id)["ok"], r.id
    assert all(r.id in game.game.shelf for c in reactions.CHAPTERS[3:] for r in c["reactions"])


def test_the_new_elements_are_on_the_bench_with_snapshot_facts():
    assert {"P", "K", "Cu", "Ag"} <= set(reactions.BENCH_ELEMENTS) and len(reactions.BENCH_ELEMENTS) == 15


# ---- the hint ladder ---------------------------------------------------------------------------------------------------------
def test_a_hint_is_never_shown_until_the_button_is_pressed():
    open_chapter(1)
    call(action="pick", reaction="methane")
    v = call(action="open")
    assert v["hint"] is None and v["hint_ui"]["next"] == 1 and v["hint_ui"]["label"] == "Would you like a suggestion?"
    text = json.dumps(v["reaction"])
    assert "cannot be the one" not in text


def test_the_product_round_ladder_nudges_then_rules_out_a_list_then_chooses_it():
    open_chapter(1)
    call(action="pick", reaction="methane")
    v = call(action="hint")
    assert v["hint"]["rung"] == 1 and "Going in: carbon, hydrogen and oxygen" in v["hint"]["nudge"] and v["hint"]["hint"] == "" and v["hint"]["answer"] == ""
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["hint"].startswith("List 1 cannot be the one")
    assert v["hint_ui"]["next"] == 3 and v["hint_ui"]["confirm"] and v["hint_ui"]["stage"] == "choose"
    v = call(action="hint")                                              # Normal: needs a confirm
    assert not v["ok"] and not v["reaction"]["picked"] and v["tally"]["hints"] == 2
    v = call(action="hint", confirm=True)
    assert v["ok"] and v["reaction"]["picked"] and v["tally"]["hints"] == 3 and v["hint"] is None
    assert "methane" not in game.get_state().get("first", [])           # a chosen-for-you list is not "right first time"
    assert game.get_state()["hints"] == {"methane": 3}


def test_the_elimination_hint_skips_lists_already_tried():
    open_chapter(1)
    call(action="pick", reaction="methane")
    call(action="choose", option=0)
    v = call(action="hint")
    v = call(action="hint")
    assert v["hint"]["hint"].startswith("List 2 cannot be the one")
    call(action="choose", option=1)
    call(action="choose", option=3)
    call(action="hint")
    v = call(action="hint")
    assert "list 3 is the one that is left" in v["hint"]["hint"]


def test_the_dial_ladder_names_an_element_then_one_dial_then_sets_them_all():
    call(action="pick", reaction="water")
    v = call(action="hint")
    assert v["hint"]["stage"] == "dials" and v["hint"]["nudge"].startswith("Start with ") and "reads" in v["hint"]["nudge"]
    v = call(action="hint")
    assert v["hint"]["hint"].startswith("Turn the dial for") and v["hint"]["dial"] in (0, 1, 2)
    answer = reactions.BY_ID["water"].answer
    assert ("to %d." % answer[v["hint"]["dial"]]) in v["hint"]["hint"]
    assert [s["coef"] for s in v["reaction"]["species"]] == [1, 1, 1]      # nothing changed by a nudge or a hint
    v = call(action="hint", confirm=True)
    assert v["ok"] and [s["coef"] for s in v["reaction"]["species"]] == answer and v["reaction"]["balanced"]
    assert v["tally"]["turns"] == 0 and v["totals"]["shelved"] == 0 and v["hint"]["done"]     # the answer sets dials but does not run or count turns
    assert call(action="hint")["hint_ui"]["next"] == 0


def test_there_is_nothing_to_suggest_once_the_ledger_reads_equal_or_the_order_is_shelved():
    call(action="pick", reaction="carbon-dioxide")                         # all ones: already equal
    v = call(action="hint")
    assert not v["ok"] and "Press Run" in v["message"] and v["tally"]["hints"] == 0 and v["hint_ui"]["balanced"]
    solve("water")
    v = call(action="hint")
    assert not v["ok"] and v["tally"]["hints"] == 0 and not v["hint_ui"]["available"]


def test_turning_a_dial_or_changing_order_clears_a_ladder_in_progress():
    call(action="pick", reaction="water")
    call(action="hint")
    assert call(action="dial", index=0, value=2)["hint"] is None
    call(action="hint")
    call(action="pick", reaction="table-salt")
    assert call(action="open")["hint"] is None and call(action="hint")["hint"]["rung"] == 1


@pytest.mark.parametrize("r", reactions.ALL, ids=lambda r: r.id)
def test_following_the_hints_dial_by_dial_always_finishes_every_order(r):
    open_chapter(r.chapter)
    if r.after:
        solve(r.after)
    call(action="pick", reaction=r.id)
    if r.is_round:
        for _ in range(3):
            call(action="hint")
            v = call(action="hint")
            if v["reaction"]["picked"]:
                break
            call(action="choose", option=[i for i in range(4) if i != r.right and i not in [c["index"] for c in (v["reaction"]["choices"] or []) if c["tried"]]][0])
        call(action="choose", option=r.right)
    for _ in range(r.size + 1):
        v = call(action="hint")
        if not v["ok"]:
            break
        v = call(action="hint")
        text = v["hint"]["hint"]
        idx, want = v["hint"]["dial"], int(re.search(r"to (\d+)\.", text).group(1))
        assert want == r.answer[idx]
        v = call(action="dial", index=idx, value=want)
    assert v["reaction"]["balanced"] and [s["coef"] for s in v["reaction"]["species"]] == r.answer


def test_every_press_of_the_ladder_is_counted_and_the_record_keeps_the_highest_rung():
    call(action="pick", reaction="water")
    call(action="hint")
    assert call(action="open")["totals"]["hints"] == 1 and game.get_state()["hints"] == {"water": 1}
    call(action="hint")
    assert game.get_state()["hints"] == {"water": 2} and call(action="open")["tally"]["hints"] == 2
    call(action="hint", confirm=True)
    call(action="run")
    assert game.get_state()["hints"] == {"water": 3} and call(action="hint")["tally"]["hints"] == 3         # a shelved order takes none


def test_hints_round_trip_and_bad_hint_records_are_dropped():
    call(action="pick", reaction="water")
    call(action="hint")
    saved = game.get_state()
    game.game.__init__()
    game.load_state(json.loads(json.dumps(saved)))
    assert game.get_state()["hints"] == {"water": 1} and game.get_state()["tally"]["hints"] == 1
    for bad in ({"water": 9}, {"water": 0}, {"water": True}, {"nope": 2}, {"methane": 2}, [1], "x"):
        game.load_state({"schema": 1, "hints": bad})
        assert "hints" not in game.get_state(), bad


# ---- difficulty ----------------------------------------------------------------------------------------------------------------
def test_easy_opens_the_nudge_and_the_hint_together_and_needs_no_confirm():
    level("easy")
    call(action="pick", reaction="water")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint"]["nudge"] and v["hint"]["hint"] and v["tally"]["hints"] == 1
    v = call(action="hint")
    assert v["ok"] and v["reaction"]["balanced"] and v["tally"]["hints"] == 2


def test_hard_has_no_answer_step():
    level("hard")
    call(action="pick", reaction="water")
    call(action="hint")
    v = call(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint_ui"]["next"] == 0 and v["hint_ui"]["limit"]
    v = call(action="hint", confirm=True)
    assert not v["ok"] and "Hard has no answer step" in v["message"] and not v["reaction"]["balanced"]


def test_a_level_changes_only_the_ladder_never_the_orders_or_records():
    outcomes = []
    for name in ("easy", "normal", "hard"):
        game.game.__init__()
        level(name)
        for r in reactions.CHAPTERS[0]["reactions"][:5]:
            solve(r.id)
        outcomes.append(json.dumps({k: v for k, v in game.get_state().items()}, sort_keys=True))
    assert len(set(outcomes)) == 1
    assert call(action="difficulty", level="legendary")["ok"] is False and game.difficulty == "hard"
    game.game.__init__()
    assert game.difficulty == "hard"                                        # a reset leaves the page's choice alone
    assert "difficulty" not in game.get_state() and "level" not in json.dumps(game.get_state())


def test_a_change_of_level_clears_a_ladder_opened_under_the_old_one():
    call(action="pick", reaction="water")
    call(action="hint")
    level("hard")
    assert call(action="open")["hint"] is None


def test_the_hint_words_follow_the_house_rules():
    banned = re.compile(r"\b(timer|energy|streak|daily|lives|hurry|expires?)\b", re.I)
    for r in reactions.ALL:
        for text in hints.choose_texts(r, []) [:3] if r.is_round else ():
            assert not banned.search(text) and chem.lint([text], []) == []
        for text in (hints.dial_texts(r, [1] * r.size) or ())[:3] if not all(c == 1 for c in r.answer) else ():
            assert not banned.search(text) and chem.lint([text], []) == []


# ---- goals ---------------------------------------------------------------------------------------------------------------------
def not_done(queue):
    return [g for g in queue if not g["done"]]


def test_a_fresh_game_shows_three_goals_one_of_each_kind():
    top = not_done(goals.queue({}, 0, 0))[:3]
    assert [g["id"] for g in top] == ["open-burning", "tiles-5", "finish-basics"]
    assert top[0]["label"] == "Shelve 5 orders in Bench Basics" and top[0]["reward"] == "Opens Burning"
    assert [g["target"] for g in top] == [5, 5, 8] and all(g["current"] == 0 for g in top)
    assert call(action="open")["goals"][:3] == goals.queue({}, 0, 0)[:3]


def test_goal_ids_are_unique_numbers_are_clamped_and_text_is_plain():
    full = {r.id: 1 for r in reactions.ALL}
    for shelf, found, turns in (({}, 0, 0), (full, 15, 10 ** 6), ({"water": 1}, 3, 120)):
        q = goals.queue(shelf, found, turns)
        assert len({g["id"] for g in q}) == len(q)
        for g in q:
            assert 0 <= g["current"] <= g["target"] and g["done"] == (g["current"] >= g["target"]) and g["label"]
    assert not not_done(goals.queue(full, 15, 10 ** 6))


def test_goals_only_ever_go_up_and_done_ones_come_last():
    q0 = goals.queue({}, 0, 0)
    solve("carbon-dioxide")
    q1 = call(action="open")["goals"]
    assert {g["id"]: g["current"] for g in q1}["finish-basics"] == 1
    done_flags = [g["done"] for g in q1]
    assert done_flags == sorted(done_flags)                                  # not done first, then done
    for g0 in q0:
        g1 = next(g for g in q1 if g["id"] == g0["id"]) if any(g["id"] == g0["id"] for g in q1) else None
        assert g1 is None or g1["current"] >= g0["current"]


def test_every_dial_turn_and_hint_and_run_moves_something_the_page_shows():
    for ident in ("stat-shelved", "stat-elements", "stat-turns", "stat-runs", "stat-hints"):
        assert 'id="%s"' % ident in HTML and ident in APP


# ---- the page ------------------------------------------------------------------------------------------------------------------
def test_the_page_wires_the_hint_box_goals_difficulty_and_the_wrapped_row_fix():
    for needle in ('id="hint-box"', 'id="hint-button"', 'id="hint-list"', 'id="goals"', 'id="difficulty-slot"', 'id="route-line"', "shared/goals-panel.js", "shared/difficulty.js"):
        assert needle in HTML, needle
    for needle in ("Would you like a suggestion?", "NoyvjGoals.mount", "NoyvjDifficulty.mount", 'action: "hint"', 'action: "difficulty"', "Goes in (carried over)"):
        assert needle in APP, needle
    assert 'el("div", "term")' in APP and ".term {" in CSS                 # a sign wraps together with the formula after it


def test_the_ladder_text_is_written_with_text_content_only():
    assert "innerHTML" not in APP
