"""Milestone 6: the 14 achievements (manifest, pure checks over saved state, panel and toast wiring, reachability on every level)."""

import json
from pathlib import Path

import pytest

import achievements
import charts
import game as game_module

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
BY_ID = {a[0]: a for a in achievements.ACHIEVEMENTS}
SEASON_IDS = [[c["id"] for c in s["charts"]] for s in charts.SEASONS]


@pytest.fixture(autouse=True)
def fresh():
    game_module.difficulty = "normal"
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.difficulty = "normal"
    game_module.handle(json.dumps({"action": "reset"}))


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def solve(cid):
    do(action="pick", chart=cid)
    for a, b in charts.BY_ID[cid]["figure"]:
        do(action="toggle", a=a, b=b)
    return do(action="finish")


def earned_ids():
    return {a["id"] for a in do(action="open")["achievements"] if a["earned"]}


def one(aid):
    return [a for a in do(action="open")["achievements"] if a["id"] == aid][0]


# ---- the manifest --------------------------------------------------------------------------------------------------------------
def test_manifest_matches_the_engine_table_and_has_fourteen():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for entry, row in zip(manifest, achievements.ACHIEVEMENTS):
        assert entry == {"id": row[0], "label": row[1], "description": row[2]}
    assert len(set(achievements.IDS)) == 14


def test_the_plans_ids_are_all_there_and_the_names_that_keep_a_chart_hidden_are_reworded():
    assert set(achievements.IDS) == {"first_figure", "ten_figures", "twenty_figures", "forty_figures", "winter_done", "spring_done", "summer_done",
                                     "autumn_done", "southern_done", "the_hunter", "the_bears", "southern_cross", "no_hints_needed", "long_night"}
    labels = {a[0]: a[1] for a in achievements.ACHIEVEMENTS}
    assert labels["first_figure"] == "First Figure" and labels["forty_figures"] == "Forty Figures" and labels["the_bears"] == "The Bears"
    assert labels["no_hints_needed"] == "No Hints Needed" and labels["long_night"] == "Long Night" and labels["winter_done"] == "Winter Done"


def test_every_achievement_has_a_visible_number_and_none_is_hidden_or_timed():
    for a in do(action="open")["achievements"]:
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"]
        assert a["label"].strip() and a["description"].strip() and a["description"].endswith(".")
    text = (GAME_DIR / "achievements.json").read_text(encoding="utf-8").lower()
    assert "hidden" not in text
    allowed = {"found", "hunter", "bears", "cross", "clean", "lines", "sea0", "sea1", "sea2", "sea3", "sea4"}
    for _i, label, description, fact, _n in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck", "fast", "speed", "difficulty", "hard"):
            assert word not in description.lower().replace(".", "").split(), (label, word)
        assert fact in allowed


def test_totals_follow_the_chart_set_that_exists():
    assert BY_ID["forty_figures"][4] == len(charts.ORDER) == 40
    for s, aid in enumerate(("winter_done", "spring_done", "summer_done", "autumn_done", "southern_done")):
        assert BY_ID[aid][4] == len(charts.SEASONS[s]["charts"]) == 8
        assert charts.SEASONS[s]["name"] in BY_ID[aid][2]
    assert BY_ID["first_figure"][4] < BY_ID["ten_figures"][4] < BY_ID["twenty_figures"][4] < BY_ID["forty_figures"][4]
    assert BY_ID["no_hints_needed"][4] == 10 and BY_ID["long_night"][4] == 500 and BY_ID["the_bears"][4] == 2
    assert BY_ID["the_hunter"][4] == BY_ID["southern_cross"][4] == 1
    assert all(cid in charts.BY_ID for cid in (achievements.HUNTER, achievements.CROSS) + achievements.BEARS)
    assert 10 <= BY_ID["no_hints_needed"][4] <= len(charts.ORDER)


def test_the_achievement_text_never_names_a_constellation_or_a_star_that_is_not_found_yet():
    """Core constraint 7: a chart's name, meaning, note and star names stay out of the view until it is finished, achievements included."""
    text = json.dumps(do(action="open")["achievements"]) + (GAME_DIR / "achievements.json").read_text(encoding="utf-8")
    for c in charts.ALL:
        assert c["name"] not in text.replace(c["id"], ""), c["name"]
        assert c["meaning"] not in text, c["meaning"]
        assert c["note"] not in text
        for s in c["stars"]:
            assert s["name"] not in text, s["name"]
    # the ones about a particular chart are real: their charts exist, the Southern Cross is the only chart with a crossing pair
    assert [c["id"] for c in charts.ALL if c.get("cross_ok")] == [achievements.CROSS]


def test_the_text_is_the_same_before_and_after_it_is_earned():
    before = [(a["id"], a["label"], a["description"]) for a in do(action="open")["achievements"]]
    for cid in SEASON_IDS[0]:
        solve(cid)
    after = [(a["id"], a["label"], a["description"]) for a in do(action="open")["achievements"]]
    assert before == after


# ---- the pure checks -----------------------------------------------------------------------------------------------------------
def test_each_achievement_needs_what_it_says_and_not_less():
    facts = achievements.facts_of({}, {}, 0)
    assert achievements.earned(facts) == []
    assert achievements.earned(dict(facts, found=10)) == ["first_figure", "ten_figures"]
    assert "twenty_figures" not in achievements.earned(dict(facts, found=19)) and "twenty_figures" in achievements.earned(dict(facts, found=20))
    assert "forty_figures" not in achievements.earned(dict(facts, found=39)) and "forty_figures" in achievements.earned(dict(facts, found=40))
    for s, aid in enumerate(("winter_done", "spring_done", "summer_done", "autumn_done", "southern_done")):
        assert aid not in achievements.earned(dict(facts, **{"sea%d" % s: 7})) and aid in achievements.earned(dict(facts, **{"sea%d" % s: 8}))
    assert "no_hints_needed" not in achievements.earned(dict(facts, clean=9)) and "no_hints_needed" in achievements.earned(dict(facts, clean=10))
    assert "long_night" not in achievements.earned(dict(facts, lines=499)) and "long_night" in achievements.earned(dict(facts, lines=500))
    assert "the_bears" not in achievements.earned(dict(facts, bears=1)) and "the_bears" in achievements.earned(dict(facts, bears=2))
    assert "the_hunter" in achievements.earned(dict(facts, hunter=1)) and "southern_cross" in achievements.earned(dict(facts, cross=1))


def test_facts_count_seasons_bears_orion_crux_and_clean_from_the_finished_set():
    solved = {cid: 3 for cid in SEASON_IDS[0][:3] + ["orion", "ursa-major", "crux"]}
    facts = achievements.facts_of(solved, {SEASON_IDS[0][0]: 1, "orion": 3}, 41)
    assert facts["found"] == 6 and facts["sea0"] == 4 and facts["sea1"] == 1 and facts["sea4"] == 1 and facts["sea2"] == 0
    assert facts["hunter"] == 1 and facts["bears"] == 1 and facts["cross"] == 1 and facts["lines"] == 41
    assert facts["clean"] == 4              # six finished, two of them asked for a suggestion
    assert achievements.facts_of({}, {}, 0) == {"found": 0, "lines": 0, "hunter": 0, "cross": 0, "bears": 0, "clean": 0,
                                                "sea0": 0, "sea1": 0, "sea2": 0, "sea3": 0, "sea4": 0}
    assert set(achievements.facts_of({}, {}, 0)) == set(achievements.FACTS)


# ---- earned ids in the save, and never read back --------------------------------------------------------------------------------
def test_earned_ids_are_written_to_the_save_and_never_read_back():
    assert "achievements_earned" not in game_module.get_state()
    solve(SEASON_IDS[0][0])
    state = game_module.get_state()
    assert state["achievements_earned"] == ["first_figure"]
    assert json.loads(json.dumps(state)) == state
    game_module.load_state({"schema": 1, "achievements_earned": list(achievements.IDS)})
    v = do(action="open")
    assert v["totals"]["done"] == 0 and not any(a["earned"] for a in v["achievements"]) and "achievements_earned" not in game_module.get_state()


def test_a_loaded_save_and_a_played_game_agree_on_what_is_earned():
    for cid in SEASON_IDS[0]:
        solve(cid)
    played = earned_ids()
    state = json.loads(json.dumps(game_module.get_state()))
    game_module.handle(json.dumps({"action": "reset"}))
    assert earned_ids() == set()
    game_module.load_state(state)
    assert earned_ids() == played == {"first_figure", "winter_done", "the_hunter"}
    assert game_module.get_state()["achievements_earned"] == state["achievements_earned"]


def test_the_hint_record_and_the_tally_survive_a_save_and_reload_so_the_achievements_they_feed_come_back():
    solve(SEASON_IDS[0][0])
    do(action="pick", chart=SEASON_IDS[0][1])
    do(action="hint")
    state = json.loads(json.dumps(game_module.get_state()))
    assert state["hints"] == {SEASON_IDS[0][1]: 1} and state["tally"]["draws"] > 0
    game_module.handle(json.dumps({"action": "reset"}))
    game_module.load_state(state)
    assert game_module.game.hinted == {SEASON_IDS[0][1]: 1} and do(action="open")["totals"]["lines"] == state["tally"]["draws"]


# ---- how each input is counted ---------------------------------------------------------------------------------------------------
def test_each_season_done_needs_every_chart_of_that_season():
    for cid in SEASON_IDS[0][:7]:
        solve(cid)
    assert "winter_done" not in earned_ids() and one("winter_done")["have"] == 7
    solve(SEASON_IDS[0][7])
    assert "winter_done" in earned_ids() and one("winter_done")["have"] == 8 and "spring_done" not in earned_ids()


def test_the_hunter_is_orion_and_the_bears_need_both():
    assert "the_hunter" not in earned_ids()
    for cid in SEASON_IDS[0][:5]:
        solve(cid)
    solve("orion")
    assert "the_hunter" in earned_ids()
    solve("ursa-major")
    assert "the_bears" not in earned_ids() and one("the_bears")["have"] == 1
    solve("ursa-minor")
    assert "the_bears" in earned_ids() and one("the_bears")["have"] == 2


def test_the_southern_cross_is_crux_and_needs_the_southern_page_to_be_open():
    for s in range(4):
        for cid in SEASON_IDS[s][:5]:
            solve(cid)
    assert "southern_cross" not in earned_ids()
    solve("crux")
    assert "southern_cross" in earned_ids() and one("southern_cross")["need"] == 1


def test_no_hints_needed_counts_only_charts_finished_without_a_suggestion():
    ids = SEASON_IDS[0] + SEASON_IDS[1][:3]                       # eleven charts, the first of which asks for a nudge
    do(action="pick", chart=ids[0])
    do(action="hint")                                             # a nudge is a suggestion: this chart is no longer clean
    for cid in ids[:10]:
        solve(cid)
    assert one("no_hints_needed")["have"] == 9 and "no_hints_needed" not in earned_ids()
    solve(ids[10])
    assert one("no_hints_needed")["have"] == 10 and "no_hints_needed" in earned_ids()
    assert game_module.game.hinted == {ids[0]: 1}


def test_a_hint_draw_that_finishes_a_chart_still_marks_it_hinted():
    cid = SEASON_IDS[0][0]
    do(action="hint", confirm=True)
    do(action="hint", confirm=True)
    do(action="hint", confirm=True)
    assert do(action="hint_draw")["ok"]
    do(action="finish")
    assert cid in game_module.game.solved and game_module.game.hinted.get(cid) == 3
    assert one("no_hints_needed")["have"] == 0


def test_long_night_counts_lines_the_player_drew_not_erased_not_the_hint_draw():
    cid = SEASON_IDS[0][0]
    rules = charts.rules(cid)
    pair = next(rules.edges[k] for k in range(len(rules.edges)) if k not in rules.must and k not in rules.never)
    for _ in range(30):
        do(action="toggle", a=pair[0], b=pair[1])                # draw, erase, draw ...
    assert one("long_night")["have"] == 15 and game_module.get_state()["tally"] == {"draws": 15, "erases": 15}
    do(action="hint", confirm=True); do(action="hint", confirm=True); do(action="hint", confirm=True)
    assert do(action="hint_draw")["ok"]                          # the whole shape drawn by the ladder is not the player's own drawing
    assert one("long_night")["have"] == 15 and game_module.game.tally["draws"] == 15


def test_a_finished_chart_cannot_be_used_to_farm_lines():
    solve(SEASON_IDS[0][0])
    before = one("long_night")["have"]
    a, b = charts.BY_ID[SEASON_IDS[0][0]]["figure"][0]
    assert do(action="toggle", a=a, b=b)["ok"] is False
    assert one("long_night")["have"] == before


# ---- reachability: a scripted player earns all fourteen on every difficulty, and the level never changes which are earned -------------
def play_everything(level):
    game_module.handle(json.dumps({"action": "reset"}))
    if level:
        game_module.set_difficulty(level)
    do(action="pick", chart=charts.ORDER[0])
    rules = charts.rules(charts.ORDER[0])
    pair = next(rules.edges[k] for k in range(len(rules.edges)) if k not in rules.must and k not in rules.never)
    for _ in range(2 * 180):                                      # mistakes drawn and taken back on the first chart: 180 more lines drawn
        do(action="toggle", a=pair[0], b=pair[1])
    for cid in charts.ORDER:                                      # season order opens each page in turn
        solve(cid)
        if cid == charts.ORDER[0]:
            assert "first_figure" in earned_ids()
    return do(action="open")


def test_a_scripted_player_earns_every_achievement_on_normal_without_luck_hints_or_time():
    v = play_everything("normal")
    assert [a["id"] for a in v["achievements"] if not a["earned"]] == []
    assert set(game_module.get_state()["achievements_earned"]) == set(achievements.IDS)
    assert game_module.game.hinted == {} and v["tally"]["hints"] == 0
    by = {a["id"]: a for a in v["achievements"]}
    assert by["no_hints_needed"]["have"] == 10 and by["forty_figures"]["have"] == 40 and by["long_night"]["have"] == 500
    assert v["totals"]["done"] == 40 and v["totals"]["seasons_done"] == 5


def test_the_difficulty_level_never_gates_an_achievement():
    results = {}
    for level in (None, "easy", "normal", "hard"):
        v = play_everything(level)
        results[level] = ([(a["id"], a["earned"], a["have"]) for a in v["achievements"]], game_module.get_state()["achievements_earned"])
    assert results["easy"] == results["normal"] == results["hard"] == results[None]
    assert all(r[0] and all(e for _i, e, _h in r[0]) for r in results.values())


def test_the_achievement_module_never_reads_the_difficulty_or_the_engine():
    code = "\n".join(line for line in (GAME_DIR / "achievements.py").read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#"))
    code = code.split('"""', 2)[2]                                # drop the module docstring: only the code is judged
    assert "import game" not in code and "difficulty" not in code and "hard" not in code.lower() and "time" not in code and "random" not in code


# ---- the page --------------------------------------------------------------------------------------------------------------------
def test_the_panel_toast_count_and_share_button_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'id="achievements-count"',
                   'data-game-name="Constellations"', "achievement-share.js", 'panel: "achievements-panel"'):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP
    assert "ach-list" in CSS and 'wirePanelToggle("achievements-toggle-button", "achievements-panel")' in APP
    assert '"achievements.py"' in APP and '"achievements"' in APP


def test_the_toast_only_fires_for_something_new_and_never_on_load():
    """app.js remembers what was earned before: null until the first view, and a loaded save resets it (so loading never toasts)."""
    assert "var knownEarned = null" in APP and "knownEarned = null; send({ action: \"open\" })" in APP
    assert "knownEarned.indexOf(a.id) === -1" in APP
    assert "achText" in APP and "showToast((view.message" in APP        # shown after the move's own message, never replaced by it


def test_the_count_is_text_and_the_earned_state_is_not_colour_alone():
    assert '" of " + items.length' in APP and 'a.earned ? "Earned"' in APP
    assert "border-style: double" in CSS


def test_the_toolbar_button_exists_beside_the_atlas_and_the_panel_is_hidden_at_first():
    assert HTML.index("atlas-toggle-button") < HTML.index("achievements-toggle-button") < HTML.index("changelog-toggle-button")
    assert '<section id="achievements-panel" class="panel" hidden' in HTML
