"""W1-grid: the Kestrel Valley story, unlocked through the shared story-chapters.js."""

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
    assert len(ids) == len(set(ids))
    for c in data["chapters"]:
        assert c["title"].strip() and len(c["text"]) > 40


def test_page_loads_the_story_and_lists_it_as_a_story_element():
    html = (HERE / "index.html").read_text()
    assert 'shared/story-chapters.js" data-game-id="grid" data-story="story.json"' in html
    assert 'data-story-selectors="#story-chapters"' in html


def test_opening_and_earned_chapters_are_reached_on_a_check(game_env):
    m = game_env.module
    story = _install()
    m.state.plant_counts["solar"] = 1
    m._check_new_achievements_for_toast()
    assert story.reached[0] == "begin"
    assert "first_watt" in story.reached and "renewable_pioneer" in story.reached


def test_no_story_script_is_harmless(game_env):
    m = game_env.module
    m._check_new_achievements_for_toast()
    m._seed_achievement_toast_baseline()


def test_a_loaded_save_brings_its_chapters_back(game_env):
    m = game_env.module
    m.state.plant_counts["wind"] = 2
    saved = m.get_state()
    story = _install()
    m.load_state(saved)
    assert "begin" in story.reached and "first_watt" in story.reached
