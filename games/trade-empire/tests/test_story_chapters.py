"""W1-trade-empire: the founding-contract story, unlocked through the shared story-chapters.js."""

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
    assert {"rift_colonies", "umbral_deep"} <= chapters


def test_chapters_are_well_formed():
    data = json.loads((HERE / "story.json").read_text())
    ids = [c["id"] for c in data["chapters"]]
    assert len(ids) == len(set(ids))
    assert ids[0] == "begin"
    for c in data["chapters"]:
        assert c["title"].strip() and len(c["text"]) >= 60


def test_page_loads_the_story_and_lists_it_as_a_story_element():
    html = (HERE / "index.html").read_text()
    assert 'shared/story-chapters.js" data-game-id="trade-empire" data-story="story.json"' in html
    assert '#story-chapters"' in html
    assert ".colony-flavor" in html


def test_opening_and_earned_chapters_are_reached_on_a_check(game_env):
    m = game_env.module
    story = _install()
    m.total_sales_count = 1
    m.render()
    assert story.reached[0] == "begin"
    assert set(m.achievement_ids_earned()) <= set(story.reached)


def test_cluster_beats_follow_research(game_env):
    m = game_env.module
    story = _install()
    m.render()
    assert "rift_colonies" not in story.reached and "umbral_deep" not in story.reached
    m.unlocked_research.update({"galaxy_expansion", "outer_reaches"})
    m.render()
    assert "rift_colonies" in story.reached and "umbral_deep" not in story.reached
    m.unlocked_research.add("umbral_reach")
    m.render()
    assert "umbral_deep" in story.reached


def test_no_story_script_is_harmless(game_env):
    m = game_env.module
    m.render()
    m._earned_snapshot()


def test_a_loaded_save_brings_its_chapters_back(game_env):
    m = game_env.module
    m.unlocked_research.update({"galaxy_expansion", "outer_reaches"})
    saved = m.get_state()
    story = _install()
    m.load_state(saved)
    assert "begin" in story.reached and "rift_colonies" in story.reached
