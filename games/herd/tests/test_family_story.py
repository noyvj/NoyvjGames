"""GF-10 The Family Farm: a branching story (FY-30) that never touches the simulation."""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _to_round(env, number):
    env.farm.round_number = number
    env.module.render()


def test_nothing_to_choose_before_the_first_page(game_env):
    m = game_env.module
    m.render()
    assert not m.family_beat_ready() and m.family_choices_now() == []
    assert str(m.FAMILY_BEAT1_ROUND) in game_env.elements["family-story-status"].innerText
    assert all(game_env.elements[f"family-story-choice-{c}"].hidden for c in "abc")
    assert game_env.elements["family-story-text"].innerText == ""


def test_first_page_offers_three_branches(game_env):
    m = game_env.module
    _to_round(game_env, m.FAMILY_BEAT1_ROUND)
    assert [c for c, _label in m.family_choices_now()] == ["sell", "organic", "subsidy"]
    assert all(not game_env.elements[f"family-story-choice-{c}"].hidden for c in "abc")
    assert "Grandpa Tobias" in game_env.elements["family-story-text"].innerText
    assert "choice is waiting" in game_env.elements["family-story-summary"].innerText


def test_each_branch_walks_to_its_own_ending(game_env):
    m = game_env.module
    expected = {"sell": "The Quiet Sale", "organic": "The Slow Green", "subsidy": "The Barn Grant"}
    for index, branch in enumerate(("sell", "organic", "subsidy")):
        _to_round(game_env, m.FAMILY_BEAT1_ROUND)
        game_env.elements[f"family-story-choice-{'abc'[index]}"].dispatch("click", None)
        assert game_env.farm.story_choices == [branch]
        assert game_env.elements["family-story-choice-c"].hidden  # two options in the second page
        _to_round(game_env, m.FAMILY_BEAT2_ROUND)
        assert len(m.family_choices_now()) == 2
        _click(game_env, "family-story-choice-a")
        assert len(game_env.farm.story_choices) == 2
        _to_round(game_env, m.FAMILY_ENDING_ROUND)
        assert expected[branch] in game_env.elements["family-story-text"].innerText
        assert branch in m.family_endings
        assert game_env.elements["family-story-retell-button"].hidden is False
        _click(game_env, "family-story-retell-button")
        assert game_env.farm.story_choices == []
    assert len(m.family_endings) == 3
    assert "Endings found: 3 of 3" in game_env.elements["family-story-endings"].innerText


def test_a_certified_farm_reaches_the_ending_early(game_env):
    m = game_env.module
    _to_round(game_env, m.FAMILY_BEAT2_ROUND)
    game_env.farm.story_choices = ["organic", "ride"]
    assert not m.family_ending_ready()
    game_env.farm.certified = True
    m.render()
    assert m.family_ending_ready() and "The Slow Green" in game_env.elements["family-story-text"].innerText


def test_the_two_options_of_a_branch_end_differently(game_env):
    m = game_env.module
    texts = set()
    for branch, spec in m.FAMILY_BRANCHES.items():
        for option in spec["options"]:
            game_env.farm.story_choices = [branch, option]
            texts.add(m.family_ending_text()[1])
    assert len(texts) == 6


def test_unlisted_choices_are_refused(game_env):
    m = game_env.module
    _to_round(game_env, m.FAMILY_BEAT1_ROUND)
    assert m.family_choose("hold") is False and m.family_choose("bogus") is False
    assert m.family_choose("sell") is True
    assert m.family_choose("sell") is False  # the next page is not ready yet


def test_the_story_never_changes_the_numbers(game_env):
    m = game_env.module
    base = game_env.module.get_state()
    _to_round(game_env, m.FAMILY_BEAT1_ROUND)
    before = dict(vars(game_env.farm))
    before.pop("story_choices")
    m.family_choose("sell")
    after = dict(vars(game_env.farm))
    after.pop("story_choices")
    assert before == after
    assert "family_choices" not in base and "family_endings" not in base


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    game_env.farm.story_choices = ["subsidy", "build"]
    m.family_endings[:] = ["subsidy"]
    state = json.loads(json.dumps(m.get_state()))
    assert state["family_choices"] == ["subsidy", "build"] and state["family_endings"] == ["subsidy"]
    m.load_state({})
    assert m.farm.story_choices == [] and m.family_endings == []
    m.load_state(state)
    assert m.farm.story_choices == ["subsidy", "build"] and m.family_endings == ["subsidy"]
    m.load_state({"family_choices": ["sell", "build"], "family_endings": ["sell", "sell", "bogus", 4]})
    assert m.farm.story_choices == ["sell"] and m.family_endings == ["sell"]  # 'build' belongs to the grant branch
    m.load_state({"family_choices": ["bogus", "hold"], "family_endings": "all"})
    assert m.farm.story_choices == [] and m.family_endings == []
    m.load_state({"family_choices": 5})
    assert m.farm.story_choices == []


def test_a_handover_restarts_the_story_but_keeps_the_endings(game_env):
    m = game_env.module
    game_env.farm.story_choices = ["sell", "hold"]
    m.family_endings[:] = ["sell"]
    game_env.farm.certified = True
    m.hand_over_farm()
    assert m.farm.story_choices == [] and m.family_endings == ["sell"]


def test_passages_are_short_and_state_no_real_world_facts():
    text = (HERE / "game.py").read_text(encoding="utf-8")
    block = text[text.index("FAMILY_BRANCHES = {"):text.index("FAMILY_BRANCH_ORDER")]
    strings = re.findall(r'"((?:[^"\\]|\\.){40,})"', block)
    assert len(strings) >= 12
    for line in strings:
        assert len(line.split()) <= 45, line  # no paragraph walls
        assert not re.search(r"\d", line), line  # no figures: facts belong in the Real Story panel


def test_story_panel_hidden_by_the_story_pill_and_reachable_on_desktop():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        assert "#vignette-display, #story-chapters, #family-story" in html
        for rid in ("family-story", "family-story-text", "family-story-retell-button", "family-story-endings"):
            assert f'id="{rid}"' in html
    cfg = json.loads((HERE / "pc-config.json").read_text(encoding="utf-8"))
    assert "#family-story" in cfg["zones"]["side"]
