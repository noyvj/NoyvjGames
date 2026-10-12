"""The hint ladder (every rung a certain deduction, asked for, never shown on its own), the difficulty levels, the goals queue, the new seasons
and the page pieces of milestones 4 and 5."""

import json
import re
from pathlib import Path

import pytest

import charts
import game as game_module
import goals
import hints
import sky

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    game_module.set_difficulty("normal")
    yield
    game_module.handle(json.dumps({"action": "reset"}))
    game_module.set_difficulty("normal")


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def open_everything(except_id):
    game_module.game.solved = {cid: 0 for cid in charts.ORDER if cid != except_id}
    return do(action="pick", chart=except_id)


def figure(cid):
    return {tuple(e) for e in charts.BY_ID[cid]["figure"]}


def ladder_to_the_end(cid):
    """Ask for a suggestion, then the hint, draw its line; repeat until the chart is valid. Returns the number of lines drawn."""
    open_everything(cid)
    fig = figure(cid)
    drawn = 0
    while True:
        v = do(action="hint")
        if not v["ok"]:
            return drawn
        v = do(action="hint")
        a, b = v["hint"]["line"]
        assert (min(a, b), max(a, b)) in fig, "a hint named a line that is not in the figure on %s" % cid
        v = do(action="toggle", a=a, b=b)
        drawn += 1
        if v["valid"]:
            return drawn
        assert drawn < 40


# ---- the new seasons ---------------------------------------------------------------------------------------------------
def test_autumn_and_the_southern_sky_have_sixteen_more_charts_including_the_southern_cross():
    assert [s["name"] for s in charts.SEASONS[3:]] == ["Autumn Sky", "Southern Sky"]
    south = {c["id"]: c for c in charts.SEASONS[4]["charts"]}
    assert "crux" in south and south["crux"]["number"] == 1 and len(south["crux"]["stars"]) == 4
    assert south["crux"]["cross_ok"] == [[[0, 3], [1, 2]]] and south["crux"]["logic"] == 1
    for c in charts.SEASONS[4]["charts"]:
        assert "southern hemisphere" in c["best"]


def test_the_southern_cross_is_drawn_with_two_lines_that_really_cross_on_the_page_coordinates():
    c = charts.BY_ID["crux"]
    pts = [(s["x"], s["y"]) for s in c["stars"]]
    (a, b), (m, n) = [tuple(e) for e in c["figure"]]
    assert sky.segments_touch(pts[a], pts[b], pts[m], pts[n]), "the traditional Southern Cross is two crossing lines"


def test_crux_is_finished_in_the_engine_and_the_view_reports_the_joined_pair():
    open_everything("crux")
    for a, b in charts.BY_ID["crux"]["figure"]:
        v = do(action="toggle", a=a, b=b)
    assert v["valid"] and v["chart"]["joined"] == [[[0, 3], [1, 2]]] or v["chart"]["joined"] == [[[1, 2], [0, 3]]]
    assert any("allowed to cross" in line for line in v["words"])
    assert do(action="finish")["ok"]


def test_no_other_chart_allows_a_crossing_and_other_charts_show_none():
    assert [c["id"] for c in charts.ALL if c.get("cross_ok")] == ["crux"]
    assert do(action="open")["chart"]["joined"] == []


# ---- the ladder ----------------------------------------------------------------------------------------------------------
def test_nothing_is_suggested_until_the_player_asks_and_the_first_rung_names_no_line():
    v = do(action="open")
    assert v["hint"] is None and v["hint_ui"]["next"] == 1 and v["hint_ui"]["label"] == "Would you like a suggestion?"
    v = do(action="hint")
    h = v["hint"]
    assert h["rung"] == 1 and h["line"] is None and h["detail"] == "" and h["ghost"] == [] and h["answer"] == "" and h["star"] is not None
    assert "certain" in h["nudge"] and v["tally"]["hints"] == 1


def test_second_rung_names_one_line_and_why_and_the_third_asks_a_question_on_normal():
    do(action="hint")
    v = do(action="hint")
    h = v["hint"]
    assert h["rung"] == 2 and h["line"] and h["detail"] and h["ghost"] == []
    v = do(action="hint")                                       # the third rung needs a confirm on Normal
    assert v["ok"] is False and v["hint"]["rung"] == 2 and "confirm" in v["message"] and v["tally"]["hints"] == 2
    v = do(action="hint", confirm=True)
    h = v["hint"]
    assert h["rung"] == 3 and h["ghost"] and h["answer"].startswith("Lines to draw") and h["can_draw"] and v["tally"]["hints"] == 3
    assert do(action="hint", confirm=True)["ok"] is False        # the ladder ends


def test_the_ghost_is_exactly_the_missing_lines_of_the_figure():
    cid = charts.ORDER[0]
    v = do(action="hint")
    do(action="hint")
    v = do(action="hint", confirm=True)
    ghost = {tuple(sorted(p)) for p in v["hint"]["ghost"]}
    assert ghost == figure(cid)
    assert v["hint"]["erase"] == []


def test_draw_it_draws_the_figure_as_one_undo_step_and_is_not_counted_as_the_players_own_lines():
    cid = charts.ORDER[0]
    before = do(action="open")["tally"]
    do(action="hint"); do(action="hint"); do(action="hint", confirm=True)
    v = do(action="hint_draw")
    assert v["valid"] and v["hint"] is None
    assert {(l["a"], l["b"]) for l in v["chart"]["lines"]} == figure(cid)
    assert v["tally"]["draws"] == before["draws"] and v["tally"]["erases"] == before["erases"]
    assert do(action="undo")["valid"] is False                   # one step takes it all back
    assert do(action="hint_draw")["ok"] is False                 # nothing to draw without asking again


def test_a_wrong_line_never_leads_the_hint_astray_and_the_answer_erases_it():
    cid = "auriga"
    rules = charts.rules(cid)
    fig = figure(cid)
    wrong = next(e for e in rules.edges if tuple(e) not in fig and rules.edge(*e) not in rules.never)
    do(action="toggle", a=wrong[0], b=wrong[1])
    do(action="hint")
    v = do(action="hint")
    a, b = v["hint"]["line"]
    assert (min(a, b), max(a, b)) in fig
    v = do(action="hint", confirm=True)
    assert [list(wrong)] == [sorted(p) for p in v["hint"]["erase"]]
    v = do(action="hint_draw")
    assert v["valid"] and {(l["a"], l["b"]) for l in v["chart"]["lines"]} == fig


def test_a_complete_figure_with_only_wrong_extras_is_told_to_erase_the_extra_line():
    cid = "sagitta"
    open_everything(cid)
    rules = charts.rules(cid)
    fig = figure(cid)
    for a, b in fig:
        do(action="toggle", a=a, b=b)
    extra = next((e for e in rules.edges if tuple(e) not in fig and not sky.analyse(rules, {rules.index[x] for x in fig} | {rules.index[tuple(e)]})["valid"]), None)
    if extra is None:
        pytest.skip("no extra line breaks sagitta")
    do(action="toggle", a=extra[0], b=extra[1])
    v = do(action="hint")
    assert v["hint"]["kind"] == "remove" and "does not belong" in v["hint"]["nudge"]
    v = do(action="hint")
    assert "Erase it" in v["hint"]["detail"]


def test_a_finished_figure_has_nothing_to_suggest():
    cid = charts.ORDER[0]
    for a, b in figure(cid):
        do(action="toggle", a=a, b=b)
    v = do(action="hint")
    assert v["ok"] is False and "Press Done" in v["message"] and v["tally"]["hints"] == 0


def test_the_view_never_shows_a_line_before_the_second_rung_or_the_figure_before_the_third():
    do(action="hint")
    text = json.dumps(do(action="open")["hint"])
    h = json.loads(text)
    assert h["line"] is None and h["ghost"] == [] and h["erase"] == [] and h["answer"] == "" and h["detail"] == ""
    do(action="hint")
    h = do(action="open")["hint"]
    assert h["ghost"] == [] and h["answer"] == ""


def test_any_change_to_the_lines_or_the_chart_clears_the_ladder():
    rules = charts.rules(charts.ORDER[0])
    a, b = rules.edges[0]
    for change in ({"action": "toggle", "a": a, "b": b}, {"action": "clear"}, {"action": "next"}, {"action": "pick", "chart": charts.ORDER[1]}):
        do(action="pick", chart=charts.ORDER[0])
        do(action="hint")
        assert do(action="open")["hint"] is not None
        v = do(**change)
        assert v["hint"] is None or v["chart"]["id"] != charts.ORDER[0], change


@pytest.mark.parametrize("cid", charts.ORDER)
def test_pressing_through_the_ladder_alone_finishes_every_chart_and_never_names_a_wrong_line(cid):
    assert ladder_to_the_end(cid) >= 1
    v = do(action="finish")
    assert v["ok"] and v["chart"]["status"] == "solved"


def test_the_hint_reads_each_charts_stored_logic():
    """A chart marked 1 never needs a what-if step; a chart marked 2 may say so."""
    saw_what_if = False
    for c in charts.ALL:
        rules = charts.rules(c["id"])
        found = hints.pick(c, rules, set(rules.must), charts.LETTERS)
        assert found is not None
        if c["logic"] == 1:
            assert found["kind"] != "what-if", c["id"]
        saw_what_if = saw_what_if or found["kind"] == "what-if"
    assert saw_what_if, "at least one level-2 chart opens with its what-if step"


# ---- difficulty ----------------------------------------------------------------------------------------------------------
def test_easy_opens_the_nudge_and_the_hint_together_and_the_answer_needs_no_question():
    game_module.set_difficulty("easy")
    v = do(action="hint")
    assert v["hint"]["rung"] == 2 and v["tally"]["hints"] == 1 and v["hint_ui"]["next"] == 3 and v["hint_ui"]["confirm"] is False
    v = do(action="hint")
    assert v["hint"]["rung"] == 3 and v["hint"]["ghost"] and v["tally"]["hints"] == 2


def test_hard_stops_before_the_answer():
    game_module.set_difficulty("hard")
    do(action="hint"); v = do(action="hint")
    assert v["hint"]["rung"] == 2 and v["hint_ui"]["next"] == 0 and v["hint_ui"]["limit"] is True
    v = do(action="hint", confirm=True)
    assert v["ok"] is False and "Hard" in v["message"] and v["hint"]["rung"] == 2 and v["hint"]["ghost"] == []


def test_the_level_changes_only_the_ladder_never_the_charts_the_rules_or_the_records():
    def play(level):
        game_module.handle(json.dumps({"action": "reset"}))
        if level:
            game_module.set_difficulty(level)
        for cid in charts.SEASONS[0]["charts"][:2]:
            for a, b in figure(cid["id"]):
                do(action="pick", chart=cid["id"]); do(action="toggle", a=a, b=b)
            do(action="finish")
        v = do(action="open")
        return v["totals"], v["goals"], game_module.get_state().get("solved")
    base = play(None)
    assert play("normal") == base
    assert play("easy") == base and play("hard") == base


def test_a_bad_level_is_refused_and_a_change_clears_a_ladder_in_progress():
    do(action="hint")
    assert do(action="difficulty", level="impossible")["ok"] is False
    v = do(action="difficulty", level="easy")
    assert v["hint"] is None and v["difficulty"] == "easy"


def test_reset_and_load_leave_the_level_alone_and_it_is_never_saved():
    game_module.set_difficulty("hard")
    do(action="reset")
    assert do(action="open")["difficulty"] == "hard"
    game_module.load_state({"schema": 1})
    assert do(action="open")["difficulty"] == "hard" and "difficulty" not in game_module.get_state()


# ---- saving the record --------------------------------------------------------------------------------------------------
def test_the_highest_rung_asked_while_a_chart_was_being_solved_is_saved_and_checked_on_load():
    cid = charts.ORDER[0]
    do(action="hint"); do(action="hint"); do(action="hint", confirm=True)
    state = game_module.get_state()
    assert state["hints"] == {cid: 3} and state["tally"]["hints"] == 3
    game_module.load_state(json.loads(json.dumps(state)))
    assert game_module.game.hinted == {cid: 3}
    game_module.load_state({"schema": 1, "hints": {cid: 9, charts.ORDER[9]: 2, "nonsense": 1, charts.ORDER[1]: "x"}, "tally": {"hints": -4}})
    assert game_module.game.hinted == {} and game_module.game.tally["hints"] == 0


def test_a_hint_asked_after_a_chart_is_finished_does_not_touch_its_record():
    cid = charts.ORDER[0]
    for a, b in figure(cid):
        do(action="toggle", a=a, b=b)
    do(action="finish")
    assert do(action="hint")["ok"] is False and game_module.game.hinted == {}


# ---- goals ---------------------------------------------------------------------------------------------------------------
def test_the_goals_queue_mixes_open_the_next_page_keep_drawing_and_finish_this_page():
    q = goals.queue({}, 0)
    todo = [g for g in q if not g["done"]]
    assert [g["id"] for g in todo[:4]] == ["open-spring", "lines-50", "finish-winter", "found-10"]
    ids = [g["id"] for g in q]
    assert len(ids) == len(set(ids)) and all(0 <= g["current"] <= g["target"] for g in q)
    solved = {c["id"]: 1 for c in charts.SEASONS[0]["charts"][:5]}
    q = goals.queue(solved, 120)
    assert q[0]["id"] == "open-spring" or q[0]["id"].startswith("open-")
    assert next(g for g in q if g["id"] == "lines-50")["done"] and next(g for g in q if g["id"] == "open-spring")["reward"] == "Opens Spring Sky"


def test_goals_only_ever_go_up_and_done_ones_come_last():
    before = goals.queue({c["id"]: 1 for c in charts.ALL[:12]}, 200)
    after = goals.queue({c["id"]: 1 for c in charts.ALL[:13]}, 260)
    done_before = {g["id"] for g in before if g["done"]}
    assert done_before <= {g["id"] for g in after if g["done"]}
    flags = [g["done"] for g in after]
    assert flags == sorted(flags), "goals still to do come before finished ones"


def test_the_view_carries_the_goals_and_every_drawn_line_counts_toward_one():
    v = do(action="open")
    assert v["goals"] and v["totals"]["hints"] == 0
    rules = charts.rules(charts.ORDER[0])
    a, b = rules.edges[0]
    v = do(action="toggle", a=a, b=b)
    assert next(g for g in v["goals"] if g["id"] == "lines-50")["current"] == 1


# ---- the page: milestones 4 and 5 ---------------------------------------------------------------------------------------
def test_the_page_loads_the_standard_kit_in_the_order_the_siblings_do():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/tutorial.js", "shared/hub-auth.js", "shared/save-widget.js", "shared/opening-screen.js", "shared/confirm-dialog.js",
             "shared/difficulty.js", "shared/goals-panel.js", 'src="app.js"', "shared/last-played.js", "shared/whats-new-banner.js", "shared/keyboard-shortcuts.js"]
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)
    assert 'data-game-id="constellations"' in tail[tail.index("opening-screen.js"):tail.index("confirm-dialog.js")]
    assert "difficulty.css" in HTML and "goals-panel.css" in HTML


def test_the_tutorial_points_only_at_things_that_exist():
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    block = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "([^"]+)"', block)
    assert len(re.findall(r'title: "', block)) >= 7 and selectors
    for sel in selectors:
        if sel.startswith("#"):
            assert sel[1:] in ids, sel
        else:
            assert sel[1:] in HTML, sel
    assert "GameTutorial.init" in APP and 'gameId: "constellations"' in APP and 'id="tutorial-restart-button"' in HTML


def test_keyboard_help_lists_the_games_own_keys_and_every_panel_it_closes_exists():
    block = HTML.split("KeyboardShortcuts.init(")[1].split("</script>")[0]
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    for toggle, panel in re.findall(r'toggle: "([^"]+)", panel: "([^"]+)"', block):
        assert toggle in ids and panel in ids
    for word in ("arrow keys", "Alt with H", "Ctrl or Cmd with Z", "drag"):
        assert word in block
    assert 'e.code === "KeyH"' in APP and "e.altKey" in APP


def test_the_suggestion_box_the_goals_and_the_difficulty_slot_are_in_the_page():
    for needle in ('id="hint-box"', 'id="hint-button"', 'id="hint-draw-button"', 'id="hint-list"', 'id="goals"', 'id="difficulty-slot"', 'id="stat-hints"',
                   'id="goals-checkbox"', 'id="hints-checkbox"', "Would you like a suggestion?"):
        assert needle in HTML, needle
    assert "NoyvjDifficulty.mount" in APP and "NoyvjGoals.mount" in APP and 'action: "difficulty"' in APP and 'action: "hint"' in APP and 'action: "hint_draw"' in APP
    assert "askThen(\"constellations-hint-answer\"" in APP, "the third rung asks first on Normal"


def test_a_suggestion_is_never_told_by_colour_alone_and_the_page_never_reveals_it_unasked():
    for needle in ("b-hintline", "b-hintplate", "b-hintsign", "b-hintstar", "\\u2212"):
        assert needle in APP, needle
    for needle in (".b-hintline", "stroke-dasharray", ".hint-rung-1", ".hint-rung-2", ".hint-rung-3", ".b-hintstar"):
        assert needle in CSS, needle
    assert 'action: "hint"' in APP and APP.count('action: "hint"') == 1, "the ladder is only ever pressed from pressHint"


def test_a_small_screen_can_make_the_board_larger_and_it_scrolls_instead_of_shrinking_the_stars():
    for needle in ('id="zoom-in-button"', 'id="zoom-out-button"', 'id="zoom-reset-button"', 'id="zoom-note"'):
        assert needle in HTML
    for needle in ("ZOOMS", "applyZoom", "revealStar", "pan-x pan-y", "constellations:zoom"):
        assert needle in APP, needle
    assert ".board-wrap.zoomed" in CSS and "overflow: auto" in CSS


def test_the_live_reads_name_their_source_and_date_and_fall_back_quietly():
    import info
    v = info.view()
    assert v["live_lines"]["api"].startswith("https://raw.githubusercontent.com/Stellarium/") and v["live_lines"]["url"] == "https://stellarium.org"
    for needle in ("loadLiveLines", "renderLiveLines", "Read live on", "could not be reached just now", "stelTried", 'id="info-live-lines"'.split('"')[1]):
        assert needle in APP, needle
    assert 'id="info-live-lines"' in HTML and "Read live from Stellarium" in HTML
    cards = [c for c in game_module.game._cards()]
    game_module.game.solved = {"orion": 3}
    card = game_module.game._cards()[0]
    assert card["code"] == "Ori" and card["hips"] == [s["hip"] for s in charts.BY_ID["orion"]["stars"]]
    assert cards == []


def test_the_about_page_explains_the_one_chart_that_crosses_and_the_suggestions():
    import info
    how = " ".join(info.view()["how"])
    assert "Southern Cross" in how and "suggestion" in how and "Would you like a suggestion?" in how


def test_the_stats_strip_counts_the_suggestions():
    assert 'id="stat-hints"' in HTML and 'bumpStat("stat-hints"' in APP
    do(action="hint")
    assert do(action="open")["totals"]["hints"] == 1


def test_known_facts_hold_for_the_new_seasons():
    brightest = {"piscis-austrinus": "Fomalhaut", "grus": "Alnair", "pavo": "Peacock", "crux": "Acrux", "centaurus": "Rigil Kentaurus",
                 "perseus": "Mirfak", "cepheus": "Alderamin", "capricornus": "Deneb Algedi", "vela": "Gamma-2 Velorum"}
    for cid, name in brightest.items():
        assert charts.BY_ID[cid]["brightest"]["name"] == name, cid
    crux = charts.BY_ID["crux"]
    assert len(crux["stars"]) == 4 and charts.SEASONS[4]["name"] == "Southern Sky"
    # Fomalhaut is far south (declination -29.6) and Perseus far north: the atlas keeps them apart
    assert charts.BY_ID["piscis-austrinus"]["atlas"]["dec"] < -20 and charts.BY_ID["perseus"]["atlas"]["dec"] > 30
    for c in charts.SEASONS[4]["charts"]:
        assert c["atlas"]["dec"] < -30 or c["id"] in ("grus",), c["id"]
