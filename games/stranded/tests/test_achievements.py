"""The 14 achievements: the manifest the hub reads, the panel the page draws, and that each can be earned."""

import json
from pathlib import Path

import achievements
import explore
import game
import story
import walker

GAME_DIR = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def test_the_manifest_matches_the_engine_exactly():
    assert [(m["id"], m["label"], m["description"]) for m in MANIFEST] == [(a[0], a[1], a[2]) for a in achievements.ACHIEVEMENTS]
    assert len(MANIFEST) == 14 and len({m["id"] for m in MANIFEST}) == 14


def test_every_achievement_has_a_number_a_real_fact_and_a_reachable_target():
    facts = game.game.facts()
    for i, _label, _desc, fact, need in achievements.ACHIEVEMENTS:
        assert fact in facts and need > 0, i
    assert achievements.EDGES == len(story.EDGES) and achievements.SCENES == len(story.SCENES) and achievements.ENDINGS == 10
    assert (achievements.LOGS, achievements.ITEMS, achievements.RECS) == (11, 10, 8)


def test_every_target_is_within_what_the_story_can_show():
    reach = explore.reach_all()
    assert len(reach["edges"]) >= achievements.EDGES and len(reach["scenes"]) >= achievements.SCENES and len(reach["endings"]) >= achievements.ENDINGS
    assert max(story.SCENES[s]["day"] for s in reach["scenes"]) == 12


def test_nothing_is_hidden_timed_or_luck_based():
    words = " ".join(a[2].lower() for a in achievements.ACHIEVEMENTS)
    for banned in ("hidden", "secret", "within", "minutes", "streak", "daily", "random", "luck", "fastest"):
        assert banned not in words


def test_a_full_walk_of_the_map_earns_every_one_that_needs_no_button_and_the_two_buttons_earn_the_rest():
    game.game.__init__()
    for _round in range(400):
        le = explore.loose_end(game.game.taken, game.game.path)
        if le is None:
            break
        game.game.path = game.game.path[:le["step"]] if le["kind"] == "rewind" else le["path"]
        game.game._sync()
        assert game.game.choose(le["choice"])[0]
    v = call(action="open")
    assert {a["id"] for a in v["achievements"] if a["earned"]} == set(achievements.IDS) - {"second_thoughts", "a_look_ahead"}
    call(action="restart")
    call(action="choose", i=0)
    call(action="restart")
    call(action="choose", i=1)
    call(action="restart")
    call(action="peek")
    v = call(action="open")
    assert all(a["earned"] for a in v["achievements"]) and v["goals"] == []


def test_the_save_writes_earned_ids_and_never_reads_them_back():
    game.game.__init__()
    call(action="choose", i=0)
    state = game.get_state()
    assert state["achievements_earned"] == ["first_words"]
    state["achievements_earned"] = list(achievements.IDS)
    game.game.__init__()
    game.load_state(state)
    assert game.get_state()["achievements_earned"] == ["first_words"]


def test_the_page_draws_the_panel_the_toast_and_the_share_hook():
    for needle in ('id="achievements-panel"', 'id="achievements-list"', 'id="achievements-toggle-button"', "shared/achievement-share.js"):
        assert needle in HTML
    for needle in ("data-achievement-id", "data-achievement-label", "Achievement unlocked: "):
        assert needle in APP


def test_an_unfinished_walk_still_has_a_reachable_path_to_every_ending_from_the_start():
    reach = explore.reach_all()
    for eid, path in reach["endings"].items():
        final = walker.replay(path)[1]
        assert story.SCENES[final[0]]["end"] == eid
