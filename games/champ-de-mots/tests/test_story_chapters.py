"""W1-champ-de-mots: the small-farm story, unlocked through the shared story-chapters.js."""

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


def _fully_automate(state, plot):
    for _ in range(6):
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)


def test_every_achievement_and_the_opening_have_a_chapter():
    chapters = {c["id"] for c in json.loads((HERE / "story.json").read_text())["chapters"]}
    achievements = {a["id"] for a in json.loads((HERE / "achievements.json").read_text())["achievements"]}
    assert "begin" in chapters and chapters - {"begin"} == achievements


def test_chapters_are_well_formed_and_in_story_order():
    data = json.loads((HERE / "story.json").read_text())
    ids = [c["id"] for c in data["chapters"]]
    assert len(ids) == len(set(ids))
    assert ids[0] == "begin"
    for c in data["chapters"]:
        assert c["title"].strip() and len(c["text"]) >= 60
    # Tiers must unlock in ascending order within each family.
    automated = [i for i in ids if i.startswith("automated_")]
    assert automated == sorted(automated, key=lambda i: int(i.split("_")[1]))
    rows = [i for i in ids if i.startswith("row_")]
    assert rows == sorted(rows, key=lambda i: int(i.split("_")[1]))


def test_story_text_has_no_guilt_framing():
    text = " ".join(c["text"].lower() for c in json.loads((HERE / "story.json").read_text())["chapters"])
    for word in ("streak", "behind", "neglect", "wilt", "failed", "guilt", "punish", "overdue"):
        assert word not in text


def test_page_loads_the_story_and_lists_it_as_a_story_element():
    html = (HERE / "index.html").read_text()
    assert 'shared/story-chapters.js" data-game-id="champ-de-mots" data-story="story.json"' in html
    assert 'data-story-selectors="#story-chapters"' in html


def test_the_opening_is_reached_on_a_fresh_render(game_env):
    story = _install()
    game_env.module.render()
    assert story.reached == ["begin"]


def test_earned_chapters_are_reached_on_the_next_render(game_env):
    module, state = game_env.module, game_env.state
    story = _install()
    module.render()
    for plot in state.plots[:25]:
        _fully_automate(state, plot)
    module.render()
    assert "automated_25" in story.reached and "automated_50" not in story.reached


def test_no_story_script_is_harmless(game_env):
    game_env.module.render()
    game_env.module._maybe_toast_new_achievements()


def test_a_loaded_save_brings_its_chapters_back(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(1):
        _fully_automate(state, plot)
    saved = module.get_state()
    story = _install()
    module.load_state(saved)
    assert "begin" in story.reached and "row_1" in story.reached
