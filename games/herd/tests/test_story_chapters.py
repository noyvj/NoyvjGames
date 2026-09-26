"""W1-herd: the Marlow Farm story, unlocked through the shared story-chapters.js."""

import json
import pathlib
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent.parent


class _FakeStory:
    def __init__(self):
        self.reached = []

    def reach(self, chapter_id):
        self.reached.append(chapter_id)


def _install():
    story = _FakeStory()
    sys.modules["js"].window = types.SimpleNamespace(NoyvjStory=story)
    return story


def test_every_achievement_and_the_opening_have_a_chapter():
    chapters = {c["id"] for c in json.loads((HERE / "story.json").read_text())["chapters"]}
    achievements = {a["id"] for a in json.loads((HERE / "achievements.json").read_text())["achievements"]}
    assert "begin" in chapters and achievements <= chapters


def test_chapters_are_well_formed():
    data = json.loads((HERE / "story.json").read_text())
    ids = [c["id"] for c in data["chapters"]]
    assert ids[0] == "begin" and len(ids) == len(set(ids))
    for c in data["chapters"]:
        assert c["title"].strip() and len(c["text"]) >= 60


def test_page_loads_the_story_and_lists_it_as_a_story_element():
    html = (HERE / "index.html").read_text()
    assert 'shared/story-chapters.js" data-game-id="herd" data-story="story.json"' in html
    assert html.count("shared/story-toggle.js") == 1
    assert "#vignette-display, #story-chapters" in html


def test_opening_and_earned_chapters_are_reached_on_a_check(game_env):
    story = _install()
    game_env.grow_herd()
    assert story.reached[0] == "begin"
    assert "first_herd" in story.reached


def test_reaching_is_idempotent_across_repeat_checks(game_env):
    m = game_env.module
    story = _install()
    game_env.grow_herd()
    m._check_new_achievements_for_toast()
    assert set(story.reached) == {"begin", "first_herd"}


def test_no_story_script_is_harmless(game_env):
    m = game_env.module
    game_env.grow_herd()
    m._check_new_achievements_for_toast()
    m._seed_achievement_toast_baseline()
    assert "first_herd" in m.achievement_ids_earned()


def test_a_loaded_save_brings_its_chapters_back(game_env):
    m = game_env.module
    game_env.grow_herd()
    saved = m.get_state()
    story = _install()
    m.load_state(saved)
    assert "begin" in story.reached and "first_herd" in story.reached
    assert not any("chapter" in key or key.startswith("story") for key in saved)  # save format unchanged
