"""Milestone 6: the fourteen achievements. Everything is computed from the cleared benches, written to the save and never read back, and every one
can be earned on every difficulty by playing the stored solutions through the real engine actions."""

import json
import re
from pathlib import Path

import pytest

import achievements
import benches
import game
import optics
import solve

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
BY_ID = {a[0]: a for a in achievements.ACHIEVEMENTS}


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def setup_function(_fn):
    game.game.__init__()
    game.difficulty = "normal"


def teardown_function(_fn):
    game.difficulty = "normal"


def play_bench(bench):
    """What a player does: go to the bench, put each stored piece on its slot and flip it to the stored side. Returns the last view."""
    call(action="pick", bench=bench.id)
    v = None
    for r, c, piece, state in bench.solution:
        v = call(action="place", r=r, c=c, piece=piece)
        assert v["ok"], (bench.id, v["message"])
        for _ in range(state):
            v = call(action="flip", r=r, c=c)
            assert v["ok"], (bench.id, v["message"])
    assert v["bench"]["status"] == "cleared", bench.id
    return v


def earned_ids(v):
    return [a["id"] for a in v["achievements"] if a["earned"]]


def layouts(*ids):
    return {i: benches.BY_ID[i].solution_layout() for i in ids}


# ---- the catalogue -------------------------------------------------------------------------------------------------------------
def test_manifest_matches_the_engine_table_and_has_fourteen():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for entry, row in zip(manifest, achievements.ACHIEVEMENTS):
        assert entry == {"id": row[0], "label": row[1], "description": row[2]}
    assert len(set(achievements.IDS)) == 14 and all(re.fullmatch(r"[a-z_]+", i) for i in achievements.IDS)


def test_the_plans_fourteen_names_are_all_there():
    assert {a[1] for a in achievements.ACHIEVEMENTS} == {
        "First Beam", "Ten Benches", "Twenty Benches", "All Forty", "Mirror Maker", "Splitting Hairs", "Rainbow", "Clear Filter",
        "The Long Run", "Fewest Pieces", "Fewest Pieces Again", "Double Bounce", "Light Both", "Quiet Decoys"}


def test_every_achievement_has_a_visible_number_and_none_is_hidden():
    for a in achievements.view({}):
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"] and a["label"] and a["description"]
    assert "hidden" not in (GAME_DIR / "achievements.json").read_text(encoding="utf-8")


def test_totals_follow_the_game_size():
    assert BY_ID["all_forty"][4] == len(benches.ALL_BENCHES) == 40
    for number, key in enumerate(("mirror_maker", "splitting_hairs", "rainbow", "clear_filter", "the_long_run"), start=1):
        assert BY_ID[key][3] == "ch%d" % number and BY_ID[key][4] == len(benches.CHAPTERS[number - 1]["benches"])
    assert BY_ID["fewest_pieces_again"][4] <= len(benches.ALL_BENCHES)


def test_nothing_is_time_luck_or_streak_based():
    allowed = {"cleared", "ch1", "ch2", "ch3", "ch4", "ch5", "fewest", "turns", "light_both", "decoy"}
    for _i, label, description, fact, _n in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck", "timed", "hurry"):
            assert word not in description.lower().split(), (label, word)
        assert fact in allowed


def test_the_engine_module_reads_no_clock_and_is_in_the_page_module_list():
    text = (GAME_DIR / "achievements.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(time|datetime|random|secrets)\b", text, flags=re.M)
    assert '"achievements.py"' in APP


# ---- each rule needs what it says and not less ---------------------------------------------------------------------------------
def test_a_fresh_game_has_nothing_earned_and_says_so_in_words():
    v = call(action="open")
    assert earned_ids(v) == [] and v["achievements_summary"] == {"earned": 0, "total": 14, "text": "0 of 14 achievements earned"}
    assert len(v["achievements"]) == 14


def test_counts_of_cleared_benches_need_exactly_their_number():
    ids = benches.ORDER
    one = achievements.earned(achievements.facts(layouts(*ids[:1])))
    assert one == ["first_beam"]
    nine = achievements.facts(layouts(*ids[:9]))
    assert "ten_benches" not in achievements.earned(nine)
    assert "ten_benches" in achievements.earned(achievements.facts(layouts(*ids[:10])))
    assert "twenty_benches" not in achievements.earned(achievements.facts(layouts(*ids[:19])))
    assert "twenty_benches" in achievements.earned(achievements.facts(layouts(*ids[:20])))
    assert "all_forty" not in achievements.earned(achievements.facts(layouts(*ids[:39])))
    assert "all_forty" in achievements.earned(achievements.facts(layouts(*ids)))


def test_a_chapter_achievement_needs_every_bench_of_its_chapter():
    keys = ("mirror_maker", "splitting_hairs", "rainbow", "clear_filter", "the_long_run")
    for number, key in enumerate(keys, start=1):
        ids = [b.id for b in benches.CHAPTERS[number - 1]["benches"]]
        assert key not in achievements.earned(achievements.facts(layouts(*ids[:-1])))
        assert key in achievements.earned(achievements.facts(layouts(*ids)))
        others = [b.id for b in benches.ALL_BENCHES if b.id not in ids]
        assert key not in achievements.earned(achievements.facts(layouts(*others)))


def test_fewest_piece_tags_count_only_layouts_within_par():
    ids = benches.ORDER[:20]
    cleared = layouts(*ids)
    assert achievements.facts(cleared)["fewest"] == 20
    assert "fewest_pieces_again" in achievements.earned(achievements.facts(cleared))
    cleared.pop(ids[0])
    assert "fewest_pieces_again" not in achievements.earned(achievements.facts(cleared))
    assert "fewest_pieces" in achievements.earned(achievements.facts(cleared))
    four = layouts(*ids[:4])
    assert "fewest_pieces" not in achievements.earned(achievements.facts(four))
    padded = layouts(*ids[:5])
    padded["c1-2"] = dict(padded["c1-2"])                           # a layout longer than par is a clear but not a tag
    padded["c1-2"][(4, 0)] = ("mirror", 0)
    assert achievements.facts(padded)["fewest"] == 4 and "fewest_pieces" not in achievements.earned(achievements.facts(padded))


def test_double_bounce_needs_one_beam_that_turns_six_times():
    turns = {b.id: optics.trace(b.board, b.solution_layout()).max_turns for b in benches.ALL_BENCHES}
    assert turns["c2-7"] >= 6, "Echo (a ring the beam goes round) is the bench that gives Double Bounce"
    assert sorted(set(turns.values()))[-2] == 5 and [i for i, t in turns.items() if t >= 6] == ["c2-7"]
    everything_else = [i for i in benches.ORDER if i != "c2-7"]
    assert "double_bounce" not in achievements.earned(achievements.facts(layouts(*everything_else)))
    assert "double_bounce" in achievements.earned(achievements.facts(layouts("c2-7")))
    assert achievements.view(achievements.facts(layouts("c1-8")))[11]["have"] == 5


def test_double_bounce_holds_for_every_way_of_clearing_echo():
    bench = benches.BY_ID["c2-7"]
    for sol in solve.solve(bench.board, bench.tray):
        assert optics.trace(bench.board, solve.layout_of(sol)).max_turns >= 6


def test_light_both_needs_a_prism_and_an_s_and_an_l_sensor_lit():
    assert "light_both" in achievements.earned(achievements.facts(layouts("c3-1")))
    assert "light_both" not in achievements.earned(achievements.facts(layouts(*[b.id for b in benches.CHAPTERS[0]["benches"]], *[b.id for b in benches.CHAPTERS[1]["benches"]])))
    assert "light_both" not in achievements.earned(achievements.facts(layouts("c4-1", "c4-2")))          # filters, no prism
    # the prism taken off the bench: nothing is cleared, nothing is earned
    assert achievements.facts({})["light_both"] == 0


def test_quiet_decoys_needs_a_cleared_bench_with_a_decoy():
    first = next(b.id for b in benches.ALL_BENCHES if b.board.decoys)
    assert first == "c4-3"
    assert "quiet_decoys" in achievements.earned(achievements.facts(layouts(first)))
    no_decoy = [b.id for b in benches.ALL_BENCHES if not b.board.decoys]
    assert "quiet_decoys" not in achievements.earned(achievements.facts(layouts(*no_decoy)))


def test_a_layout_that_does_not_clear_the_bench_earns_nothing_extra():
    bench = benches.BY_ID["c2-7"]
    wrong = {cell: (piece, 1 - state if piece == "mirror" else state) for cell, (piece, state) in bench.solution_layout().items()}
    assert not optics.trace(bench.board, wrong).ok
    call(action="pick", bench="c2-7")
    for (r, c), (piece, state) in wrong.items():
        call(action="place", r=r, c=c, piece=piece)
        for _ in range(state):
            call(action="flip", r=r, c=c)
    assert earned_ids(call(action="open")) == []


# ---- the reachability test: play the stored solutions through the real actions --------------------------------------------------
@pytest.mark.parametrize("level", ["easy", "normal", "hard"])
def test_every_achievement_is_earned_by_playing_the_stored_solutions(level):
    game.difficulty = "normal"
    call(action="difficulty", level=level)
    seen = {}
    for bench in benches.ALL_BENCHES:
        v = play_bench(bench)
        for i in earned_ids(v):
            seen.setdefault(i, bench.id)
    v = call(action="open")
    assert earned_ids(v) == list(achievements.IDS), [a["id"] for a in v["achievements"] if not a["earned"]]
    assert v["achievements_summary"]["text"] == "14 of 14 achievements earned"
    assert seen["first_beam"] == "c1-1" and seen["ten_benches"] == benches.ORDER[9] and seen["twenty_benches"] == benches.ORDER[19]
    assert seen["all_forty"] == "c5-8" and seen["mirror_maker"] == "c1-8" and seen["double_bounce"] == "c2-7"
    assert seen["splitting_hairs"] == "c2-8" and seen["rainbow"] == "c3-8" and seen["clear_filter"] == "c4-8" and seen["the_long_run"] == "c5-8"
    assert seen["light_both"] == "c3-1" and seen["quiet_decoys"] == "c4-3"
    assert seen["fewest_pieces"] == benches.ORDER[4] and seen["fewest_pieces_again"] == benches.ORDER[19]
    assert set(game.get_state()["achievements_earned"]) == set(achievements.IDS)


def test_the_answer_rung_on_hard_and_easy_changes_no_achievement():
    """Difficulty only changes the hint ladder; the same clears give the same achievements."""
    results = []
    for level in ("easy", "normal", "hard"):
        game.game.__init__()
        call(action="difficulty", level=level)
        for bench in benches.ALL_BENCHES[:12]:
            play_bench(bench)
        results.append(earned_ids(call(action="open")))
    assert results[0] == results[1] == results[2] and "ten_benches" in results[0]


# ---- the save ------------------------------------------------------------------------------------------------------------------
def test_earned_ids_are_written_to_the_save_and_never_read_back():
    play_bench(benches.BY_ID["c1-1"])
    state = game.get_state()
    assert state["achievements_earned"] == ["first_beam"]
    assert json.loads(json.dumps(state)) == state
    game.game.__init__()
    game.load_state({"achievements_earned": list(achievements.IDS)})
    v = call(action="open")
    assert v["totals"]["cleared"] == 0 and earned_ids(v) == []
    assert "achievements_earned" not in game.get_state()


def test_a_fresh_game_still_saves_as_nothing_and_a_round_trip_is_exact():
    assert game.get_state() == {}
    play_bench(benches.BY_ID["c1-1"])
    play_bench(benches.BY_ID["c1-2"])
    state = json.loads(json.dumps(game.get_state()))
    call(action="pick", bench="c1-2")                                # the verdict card is not saved, so leave the cleared bench and look again
    before = call(action="open")
    state = json.loads(json.dumps(game.get_state()))
    game.game.__init__()
    game.load_state(json.loads(json.dumps(state)))
    after = call(action="open")
    assert after == before and game.get_state() == state


def test_reading_the_achievements_changes_nothing_else():
    play_bench(benches.BY_ID["c1-1"])
    before = json.dumps(game.get_state(), sort_keys=True)
    for _ in range(3):
        call(action="open")
    achievements.facts(game.game.cleared)
    assert json.dumps(game.get_state(), sort_keys=True) == before


def test_a_loaded_save_keeps_the_achievements_its_clears_justify():
    for bench in benches.ALL_BENCHES[:10]:
        play_bench(bench)
    state = json.loads(json.dumps(game.get_state()))
    state.pop("achievements_earned")                                # an older save without the key
    game.game.__init__()
    game.load_state(state)
    assert "ten_benches" in earned_ids(call(action="open"))


# ---- the page ------------------------------------------------------------------------------------------------------------------
def test_the_panel_toast_and_share_button_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'id="achievements-count"',
                   'data-game-name="Mirror Lab"', "achievement-share.js"):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP
    assert "achievements-panel" in HTML.split("window.KeyboardShortcuts.init")[1]
    assert ".ach-list" in CSS and "li.earned" in CSS


def test_loading_a_save_or_starting_over_never_toasts_old_achievements():
    assert re.search(r"mirrorLabRefresh = function \(\) \{[^}]*knownEarned = null", APP)
    assert re.search(r'knownEarned = null; send\(\{ action: "reset" \}\)', APP)
    assert "if (knownEarned !== null)" in APP


def test_the_toast_is_not_cleared_straight_after_it_is_shown():
    send = APP[APP.index("function send(request)"):APP.index("// ---- taps, keys and drags")]
    assert send.index('showToast("")') < send.index("render();")
    assert "showToast(result.ok" not in send
