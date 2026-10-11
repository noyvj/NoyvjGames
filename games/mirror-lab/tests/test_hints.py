"""The hint ladder (QI-10-4): built on each bench's stored, proved solution. Three rungs, one per press, free, never touching a record."""

import json
import re
from pathlib import Path

import benches
import game
import hints

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh(level="normal"):
    game.game.__init__()
    call(action="difficulty", level=level)


def teardown_function(_fn):
    call(action="difficulty", level="normal")
    game.game.__init__()


def test_every_bench_has_a_nudge_a_hint_and_an_answer_built_from_its_stored_solution():
    for b in benches.ALL_BENCHES:
        order = hints.ordered_solution(b)
        assert sorted(order) == sorted(b.solution), b.id                          # the same pieces, in beam order
        nudge, hint, lines = hints.nudge_text(b), hints.hint_text(b), hints.answer_lines(b)
        assert len(lines) == len(b.solution) and hint.startswith("Try this: ")
        assert not re.search(r"\b(row|column)\b", nudge) and "bench" in nudge, (b.id, nudge)          # a nudge names a kind and an area, never a cell
        r, c, piece, _s = order[0]
        assert "row %d, column %d" % (r + 1, c + 1) in hint, b.id                    # the hint names exactly one cell
        for item in order:
            assert "row %d, column %d" % (item[0] + 1, item[1] + 1) in " ".join(lines)


def test_the_nudge_names_the_most_telling_kind_of_piece():
    assert "prism" in hints.nudge_text(benches.BY_ID["c3-1"])
    assert "an S filter" in hints.nudge_text(benches.BY_ID["c4-1"])
    assert "splitter" in hints.nudge_text(benches.BY_ID["c2-1"])
    assert "mirror" in hints.nudge_text(benches.BY_ID["c1-1"]) and "emitter" in hints.nudge_text(benches.BY_ID["c1-1"])
    assert hints.area_words(benches.BY_ID["c1-1"], 0, 0) == "in the top left of the bench"
    assert hints.area_words(benches.BY_ID["c1-1"], 2, 2) == "in the middle of the bench"


def test_the_hints_are_deterministic():
    for b in benches.ALL_BENCHES[:10]:
        assert hints.view(b, 3) == hints.view(b, 3) and hints.ordered_solution(b) == hints.ordered_solution(b)


def test_each_rung_opens_only_on_a_press_and_is_counted():
    fresh()
    v = call(action="open")
    h = v["bench"]["hint"]
    assert h["rung"] == 0 and not h["nudge"] and not h["hint"] and not h["answer"] and h["ghosts"] == [] and v["tally"]["hints"] == 0
    v = call(action="hint")
    h = v["bench"]["hint"]
    assert h["rung"] == 1 and h["nudge"] and not h["hint"] and h["ghosts"] == [] and v["tally"]["hints"] == 1
    v = call(action="hint")
    h = v["bench"]["hint"]
    assert h["rung"] == 2 and h["hint"] and len(h["ghosts"]) == 1 and "ml-ghost" in v["bench"]["svg"]
    v = call(action="hint")
    h = v["bench"]["hint"]
    assert h["rung"] == 3 and h["answer"] and len(h["answer_lines"]) == len(game.game.bench.solution) and not h["can_ask"]
    v = call(action="hint")
    assert v["ok"] is False and v["tally"]["hints"] == 3 and "every hint" in v["message"]


def test_a_ghost_is_a_dotted_frame_and_vanishes_once_the_piece_is_there():
    fresh()
    call(action="hint")
    v = call(action="hint")
    r, c = v["bench"]["hint"]["ghosts"][0]["r"], v["bench"]["hint"]["ghosts"][0]["c"]
    assert 'class="ml-ghost"' in v["bench"]["svg"] and "ml-ghost-frame" in v["bench"]["svg"] and "ml-ghost-piece" in v["bench"]["svg"]
    v = call(action="place", r=r, c=c, piece="mirror")
    assert "ml-ghost" not in v["bench"]["svg"]                                      # the right piece is on it: nothing more to suggest


def test_a_ghost_over_a_different_piece_is_only_a_frame():
    fresh()
    game.game._enter("c3-1")
    call(action="hint")
    call(action="hint")
    sol = game.game.bench.solution[0]
    assert sol[2] == "prism"
    r, c = sol[0], sol[1]
    v = call(action="place", r=r, c=c, piece="prism")
    v = call(action="flip", r=r, c=c)                                               # the wrong way up: a different state
    svg = v["bench"]["svg"]
    assert "ml-ghost-frame" in svg and "ml-ghost-piece" not in svg


def test_place_them_puts_the_stored_answer_on_the_bench_and_still_counts_as_a_clear():
    fresh()
    game.game._enter("c4-6")
    assert call(action="place_answer")["ok"] is False                               # not before the answer rung
    for _ in range(3):
        call(action="hint")
    v = call(action="place_answer")
    assert v["ok"] and v["bench"]["solved_now"] and v["verdict"]["kind"] == "cleared" and v["bench"]["pieces"] == len(game.game.bench.solution)
    assert "c4-6" in game.game.cleared and v["tally"]["hints"] == 3
    assert "ml-ghost" not in v["bench"]["svg"]


def test_place_them_replaces_what_was_there_and_counts_the_pieces():
    fresh()
    game.game._enter("c1-3")
    call(action="place", r=0, c=1, piece="mirror")
    call(action="place", r=2, c=1, piece="mirror")                                  # two wrong-ish pieces on the bench
    before = call(action="open")["tally"]
    for _ in range(3):
        call(action="hint")
    v = call(action="place_answer")
    n = len(game.game.bench.solution)
    assert v["tally"]["picked"] == before["picked"] + 2 and v["tally"]["placed"] == before["placed"] + n
    assert sorted((p["r"], p["c"], p["piece"], p["state"]) for p in v["bench"]["placed"]) == sorted(game.game.bench.solution)


def test_hints_never_change_a_record_or_a_tag():
    fresh()
    game.game._enter("c1-1")
    for _ in range(3):
        call(action="hint")
    call(action="place_answer")
    assert game.game.cleared["c1-1"] and len(game.game.cleared["c1-1"]) == benches.BY_ID["c1-1"].par
    assert call(action="open")["totals"]["fewest"] == 1                              # the same tag whether or not hints were used


def test_hint_rungs_are_saved_per_bench_and_loaded_defensively():
    fresh()
    call(action="hint")
    call(action="hint")
    state = game.get_state()
    assert state["rungs"] == {"c1-1": 2} and state["tally"]["hints"] == 2
    fresh()
    game.load_state(state)
    assert call(action="open")["bench"]["hint"]["rung"] == 2
    for bad in ({"rungs": 5}, {"rungs": {"nope": 2, "c1-1": 9, "c1-2": True, "c1-3": "x"}}, {"rungs": {"c1-1": 0}}):
        fresh()
        game.load_state(bad)
        assert game.get_state().get("rungs", {}) == {}
    fresh()
    game.load_state({"rungs": {"c1-1": 3}})
    assert game.get_state()["rungs"] == {"c1-1": 3}
    game.load_state({})
    assert "rungs" not in game.get_state()                                          # a fresh game still saves as {}


def test_easy_opens_nudge_and_hint_together_and_hard_has_no_answer_step():
    fresh("easy")
    v = call(action="hint")
    h = v["bench"]["hint"]
    assert h["rung"] == 2 and h["nudge"] and h["hint"] and len(h["ghosts"]) == 1 and v["tally"]["hints"] == 1
    v = call(action="hint")
    assert v["bench"]["hint"]["rung"] == 3 and v["bench"]["hint"]["answer"] and v["tally"]["hints"] == 2
    fresh("hard")
    call(action="hint")
    v = call(action="hint")
    assert v["bench"]["hint"]["rung"] == 2 and v["bench"]["hint"]["max"] == 2 and not v["bench"]["hint"]["can_ask"]
    v = call(action="hint")
    assert v["ok"] is False and "Hard has no answer step" in v["message"] and v["tally"]["hints"] == 2
    assert call(action="place_answer")["ok"] is False


def test_a_saved_third_rung_is_capped_when_the_level_is_hard():
    fresh()
    game.load_state({"rungs": {"c1-1": 3}})
    call(action="difficulty", level="hard")
    h = call(action="open")["bench"]["hint"]
    assert h["rung"] == 2 and not h["answer"] and len(h["ghosts"]) == 1


def test_place_them_asks_first_except_on_easy():
    assert "mirror-lab-place-answer" in APP and "ConfirmDialog.ask" in APP
    assert re.search(r'view\.difficulty !== "easy" && window\.ConfirmDialog', APP)


def test_filter_names_keep_their_capital_letter_in_every_sentence():
    import optics
    import trace_text
    assert optics.piece_name("filter_s") == "S filter" and optics.piece_name("mirror") == "mirror"
    assert "1 S filter" in trace_text.brief(benches.BY_ID["c4-6"]) and "1 s filter" not in trace_text.brief(benches.BY_ID["c4-6"])
    fresh()
    game.game._enter("c4-6")
    call(action="place", r=2, c=3, piece="filter_s")
    v = call(action="place", r=2, c=3, piece="mirror")
    assert "The S filter went back to the tray" in v["message"]
