"""Milestone 6: the 14 achievements (manifest, pure checks over saved state, panel and toast wiring, reachability on every level)."""

import json
from pathlib import Path

import achievements
import game
import pictures

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
BY_ID = {a[0]: a for a in achievements.ACHIEVEMENTS}


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def cells_of(pid):
    p = pictures.BY_ID[pid]
    return [[r, c] for r in range(p.height) for c in range(p.width) if p.rows[r][c] == "#"]


def solve(pid):
    call(action="pick", picture=pid)
    return call(action="paint", cells=cells_of(pid), value=1)


def earned_ids():
    return {a["id"] for a in call(action="open")["achievements"] if a["earned"]}


# ---- the manifest ------------------------------------------------------------------------------------------------------------------
def test_manifest_matches_the_engine_table_and_has_fourteen():
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [m["id"] for m in manifest] == list(achievements.IDS) and len(manifest) == 14
    for entry, row in zip(manifest, achievements.ACHIEVEMENTS):
        assert entry == {"id": row[0], "label": row[1], "description": row[2]}
    assert len(set(achievements.IDS)) == 14


def test_the_plans_fourteen_names_are_all_there():
    labels = {a[1] for a in achievements.ACHIEVEMENTS}
    assert labels == {"First Frame", "Ten Hung", "Thirty Hung", "Sixty Hung", "Small Hands", "Machine Shop", "Robot Row", "Station Rooms",
                      "Deep Sky Done", "The Long Wall", "Big One", "Clean Lines", "Slow Light", "Ten Thousand"}


def test_every_achievement_has_a_visible_number_and_none_is_hidden_or_timed():
    fresh()
    for a in call(action="open")["achievements"]:
        assert a["need"] >= 1 and a["have"] == 0 and not a["earned"]
        assert a["label"].strip() and a["description"].strip() and a["description"].endswith(".")
    text = (GAME_DIR / "achievements.json").read_text(encoding="utf-8").lower()
    assert "hidden" not in text
    allowed = {"hung", "gal0", "gal1", "gal2", "gal3", "gal4", "gal5", "big", "clean", "slides", "cells"}
    for _i, label, description, fact, _n in achievements.ACHIEVEMENTS:
        for word in ("day", "week", "streak", "daily", "minute", "second", "random", "luck", "fast", "speed", "difficulty", "hard"):
            assert word not in description.lower().replace(".", "").split(), (label, word)
        assert fact in allowed


def test_totals_follow_the_game_size():
    assert BY_ID["sixty_hung"][4] == len(pictures.ORDER) == 60
    for g in range(6):
        assert BY_ID[("small_hands", "machine_shop", "robot_row", "station_rooms", "deep_sky_done", "the_long_wall")[g]][4] == len(pictures.GALLERIES[g]["pictures"])
    assert BY_ID["first_frame"][4] < BY_ID["ten_hung"][4] < BY_ID["thirty_hung"][4] < BY_ID["sixty_hung"][4]
    assert achievements.BIG_SIDE == 15 and BY_ID["big_one"][2] == "Hang a 15 by 15 picture."
    assert BY_ID["ten_thousand"][4] == 10000 and BY_ID["clean_lines"][4] == 10 and BY_ID["slow_light"][4] == 1


def test_the_achievement_text_never_names_a_picture_that_is_not_hung_yet():
    fresh()
    text = json.dumps(call(action="open")["achievements"])
    for p in pictures.ALL:
        assert p.title not in text and p.caption not in text


# ---- the pure checks ---------------------------------------------------------------------------------------------------------------
def test_each_achievement_needs_what_it_says_and_not_less():
    facts = achievements.facts_of({}, {}, 0, False)
    assert achievements.earned(facts) == []
    assert achievements.earned(dict(facts, hung=10)) == ["first_frame", "ten_hung"]
    assert "thirty_hung" not in achievements.earned(dict(facts, hung=29)) and "thirty_hung" in achievements.earned(dict(facts, hung=30))
    assert "sixty_hung" not in achievements.earned(dict(facts, hung=59)) and "sixty_hung" in achievements.earned(dict(facts, hung=60))
    assert "small_hands" not in achievements.earned(dict(facts, gal0=9)) and "small_hands" in achievements.earned(dict(facts, gal0=10))
    assert "clean_lines" not in achievements.earned(dict(facts, clean=9)) and "clean_lines" in achievements.earned(dict(facts, clean=10))
    assert "ten_thousand" not in achievements.earned(dict(facts, cells=9999)) and "ten_thousand" in achievements.earned(dict(facts, cells=10000))
    assert "slow_light" not in achievements.earned(facts) and "slow_light" in achievements.earned(dict(facts, slides=1))
    assert "big_one" not in achievements.earned(facts) and "big_one" in achievements.earned(dict(facts, big=1))


def test_facts_count_gallery_big_and_clean_from_the_hung_set():
    wall = [p for p in pictures.GALLERIES[0]["pictures"]][:4] + [p for p in pictures.GALLERIES[5]["pictures"] if p.width == 15][:2]
    solved = {p.id: 1 for p in wall}
    facts = achievements.facts_of(solved, {wall[0].id: 1, wall[1].id: 3}, 55, True)
    assert facts["hung"] == 6 and facts["gal0"] == 4 and facts["gal5"] == 2 and facts["big"] == 2
    assert facts["clean"] == 4 and facts["cells"] == 55 and facts["slides"] == 1


# ---- earned ids in the save, and never read back ---------------------------------------------------------------------------------
def test_earned_ids_are_written_to_the_save_and_never_read_back():
    fresh()
    assert "achievements_earned" not in game.get_state()
    solve("hammer")
    state = game.get_state()
    assert state["achievements_earned"] == ["first_frame"]
    assert json.loads(json.dumps(state)) == state
    fresh()
    game.load_state({"schema": 1, "achievements_earned": list(achievements.IDS)})
    v = call(action="open")
    assert v["totals"]["hung"] == 0 and not any(a["earned"] for a in v["achievements"]) and "achievements_earned" not in game.get_state()


def test_a_loaded_save_and_a_played_game_agree_on_what_is_earned():
    fresh()
    for p in pictures.GALLERIES[0]["pictures"][:6]:
        solve(p.id)
    call(action="slideshow")
    played = earned_ids()
    state = json.loads(json.dumps(game.get_state()))
    fresh()
    game.load_state(state)
    assert earned_ids() == played == {"first_frame", "slow_light"}
    assert game.get_state()["achievements_earned"] == state["achievements_earned"]


def test_the_slideshow_flag_and_the_hint_record_survive_a_save_and_reload():
    """The fix noted as unverified in the live page: both are real saved inputs, so the achievements they feed come back."""
    fresh()
    solve("hammer")
    call(action="pick", picture="key")
    call(action="hint")
    call(action="slideshow")
    state = json.loads(json.dumps(game.get_state()))
    assert state["slides"] == 1 and state["hints"] == {"key": 1}
    fresh()
    game.load_state(state)
    v = call(action="open")
    assert v["slideshow_seen"] is True and v["tally"]["hints"] == 1


# ---- how each input is counted -----------------------------------------------------------------------------------------------------
def test_slideshow_earns_slow_light_even_with_nothing_hung():
    fresh()
    assert "slow_light" not in earned_ids()
    v = call(action="slideshow")
    assert "slow_light" in {a["id"] for a in v["achievements"] if a["earned"]}


def test_clean_lines_counts_only_pictures_hung_without_a_suggestion():
    fresh()
    pids = [p.id for p in pictures.GALLERIES[0]["pictures"]]
    call(action="pick", picture=pids[0])
    call(action="hint")                                           # a nudge is a suggestion: this picture is no longer clean
    solve(pids[0])
    for pid in pids[1:10]:
        solve(pid)
    v = call(action="open")
    clean = [a for a in v["achievements"] if a["id"] == "clean_lines"][0]
    assert clean["have"] == 9 and not clean["earned"]
    # a suggestion asked while a hung picture is solved AGAIN leaves the record alone
    call(action="pick", picture=pids[1])
    call(action="retry")
    call(action="hint")
    assert [a for a in call(action="open")["achievements"] if a["id"] == "clean_lines"][0]["have"] == 9
    assert game.game.hinted == {pids[0]: 1}


def test_hint_fill_that_finishes_a_picture_still_marks_it_hinted():
    fresh()
    call(action="difficulty", level="easy")
    call(action="pick", picture="hammer")
    for _ in range(40):
        v = call(action="hint")
        if v["picture"]["status"] != "open":
            break
        v = call(action="hint")
        if v["picture"]["status"] != "open":
            break
        v = call(action="hint")
        if v["picture"]["status"] != "open":
            break
    assert call(action="open")["picture"]["status"] == "solved"
    assert game.game.hinted.get("hammer", 0) >= 1
    assert [a for a in call(action="open")["achievements"] if a["id"] == "clean_lines"][0]["have"] == 0


def test_big_one_needs_a_15_by_15_not_a_12_by_12():
    fresh()
    for g in range(4):
        for p in pictures.GALLERIES[g]["pictures"]:
            solve(p.id)
    twelve = [p for p in pictures.GALLERIES[4]["pictures"] if p.width == 12][0]
    solve(twelve.id)
    assert "big_one" not in earned_ids()
    big = [p for p in pictures.GALLERIES[4]["pictures"] if p.width == 15][0]
    solve(big.id)
    assert "big_one" in earned_ids()


def test_ten_thousand_counts_the_players_own_fills_and_not_dots_or_clears():
    fresh()
    call(action="pick", picture="hammer")
    every = [[r, c] for r in range(5) for c in range(5)]
    call(action="paint", cells=every, value=2)                    # dots do not count
    assert call(action="open")["tally"]["fills"] == 0
    for _ in range(20):
        call(action="paint", cells=every, value=1)
        call(action="paint", cells=every, value=0)                # clears do not count either
    ten = [a for a in call(action="open")["achievements"] if a["id"] == "ten_thousand"][0]
    assert ten["have"] == 20 * 25 and not ten["earned"]


# ---- reachability: a scripted player earns all fourteen on every difficulty, and the level never changes which are earned --------------
def play_everything(level):
    fresh()
    if level:
        call(action="difficulty", level=level)
    for p in pictures.ALL:                                        # gallery order opens each gallery in turn
        solve(p.id)
        if p.id == pictures.ORDER[5]:
            assert "first_frame" in earned_ids()
    assert call(action="open")["totals"]["hung"] == 60
    call(action="slideshow")
    # ten thousand: solve a hung picture again, then fill and clear a whole frame until the tally is high enough
    call(action="pick", picture="long_gallery")
    call(action="retry")
    every = [[r, c] for r in range(15) for c in range(15)]
    while call(action="open")["tally"]["fills"] < 10000:
        call(action="paint", cells=every, value=1)
        call(action="paint", cells=every, value=0)
    return call(action="open")


def test_a_scripted_player_earns_every_achievement_on_normal_without_luck_hints_or_time():
    v = play_everything("normal")
    assert [a["id"] for a in v["achievements"] if not a["earned"]] == []
    assert set(game.get_state()["achievements_earned"]) == set(achievements.IDS)
    assert game.game.hinted == {} and v["tally"]["hints"] == 0
    by = {a["id"]: a for a in v["achievements"]}
    assert by["clean_lines"]["have"] == 10 and by["sixty_hung"]["have"] == 60 and by["ten_thousand"]["have"] == 10000
    assert v["totals"]["galleries_done"] == 6


def test_the_difficulty_level_never_gates_an_achievement():
    results = {}
    for level in (None, "easy", "normal", "hard"):
        v = play_everything(level)
        results[level] = ([(a["id"], a["earned"], a["have"]) for a in v["achievements"]], game.get_state()["achievements_earned"])
    assert results["easy"] == results["normal"] == results["hard"] == results[None]
    game.difficulty = "normal"


def test_the_achievement_module_never_reads_the_difficulty_or_the_engine():
    code = "\n".join(line for line in (GAME_DIR / "achievements.py").read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#"))
    code = code.split('"""', 2)[2]                                # drop the module docstring: only the code is judged
    assert "import game" not in code and "difficulty" not in code and "hard" not in code.lower()


# ---- the page --------------------------------------------------------------------------------------------------------------------
def test_the_panel_toast_count_and_share_button_are_wired_with_the_hub_hooks():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', 'id="achievements-count"',
                   'data-game-name="Picture Grid"', "achievement-share.js", 'panel: "achievements-panel"'):
        assert needle in HTML
    assert "data-achievement-id" in APP and "data-achievement-label" in APP and "Achievement unlocked: " in APP
    assert "ach-list" in CSS and 'wirePanelToggle("achievements-toggle-button", "achievements-panel")' in APP
    assert "achievements.py" in APP


def test_the_toast_only_fires_for_something_new_and_never_on_load():
    """app.js remembers what was earned before; null until the first view, and a loaded save resets it (so loading never toasts)."""
    assert "var knownEarned = null" in APP and "knownEarned = null; send({ action: \"open\" })" in APP
    assert "knownEarned.indexOf(a.id) === -1" in APP


def test_the_count_is_text_and_the_earned_state_is_not_colour_alone():
    assert '" of " + items.length' in APP and 'a.earned ? "Earned"' in APP
    assert "border-style: double" in CSS


def test_the_toolbar_button_exists_beside_gallery_and_the_panel_is_hidden_at_first():
    assert HTML.index("achievements-toggle-button") < HTML.index("changelog-toggle-button")
    assert '<section id="achievements-panel" class="panel" hidden' in HTML
