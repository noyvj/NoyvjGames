import json
import re
from pathlib import Path

import achievements
import bots
import engine
import story
from tests.test_career import play

GAME = Path(__file__).resolve().parent.parent


def test_manifest_matches_the_python_list():
    data = json.loads((GAME / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [(a["id"], a["label"], a["description"]) for a in data] == list(achievements.ACHIEVEMENTS)
    assert len(data) == 14 and len({a["id"] for a in data}) == 14


def test_every_achievement_is_reachable_from_a_matching_meta(C):
    meta = {"jobs_done": 1, "jobs_clean": 1, "best": {"chain_links": 5, "absorbed": 3}, "relationships": {"dot|vic": "friends"},
            "flags": ["everyone_home", "full_house", "over_planner", "minimalist"], "cat_targets": list(C.target_order),
            "finished_targets": ["the_affineur"], "retries": {"pigeon_museum": 5}, "reputation": 20,
            "seen_complications": list(C.complications)[:20]}
    assert achievements.earned(meta, C) == [a[0] for a in achievements.ACHIEVEMENTS]
    assert achievements.earned({}, C) == []


def test_each_condition_alone_earns_only_its_achievement(C):
    cases = {
        "first_job": {"jobs_done": 1}, "nobody_saw": {"jobs_clean": 1}, "chain_reaction": {"best": {"chain_links": 5}},
        "absorbed": {"best": {"absorbed": 3}}, "everyone_home": {"flags": ["everyone_home"]}, "full_house": {"flags": ["full_house"]},
        "over_planner": {"flags": ["over_planner"]}, "minimalist": {"flags": ["minimalist"]},
        "paid_in_cheese": {"finished_targets": ["the_affineur"]},
        "fifth_time_lucky": {"retries": {"x": 5}}, "rich_and_infamous": {"reputation": 20},
        "committee_meeting": {"seen_complications": list(C.complications)[:20]}, "cat_job": {"cat_targets": list(C.target_order)},
        "old_rivals": {"relationships": {"dot|vic": "friends"}}}
    for ach, meta in cases.items():
        assert achievements.earned(meta, C) == [ach], ach


def test_friends_who_were_never_rivals_are_not_old_rivals(C):
    assert achievements.earned({"relationships": {"bea|dot": "friends"}}, C) == []
    assert achievements.earned({"relationships": {"dot|vic": "feud"}}, C) == []


def test_near_misses_do_not_earn(C):
    assert achievements.earned({"best": {"chain_links": 4, "absorbed": 2}, "reputation": 19, "retries": {"a": 4},
                                "seen_complications": list(C.complications)[:19], "cat_targets": list(C.target_order)[:-1]}, C) == []


def test_job_flags(C):
    out = {"cells_used": 30, "cells_total": 30, "escaped": True, "max_actions_in_a_beat": 3, "sidelined": []}
    flags = achievements.job_flags(C, ["dot", "pip", "bea", "tomasz", "hank"], out)
    assert set(flags) == {"full_house", "over_planner", "minimalist", "everyone_home"}
    out2 = dict(out, cells_used=29, escaped=False, sidelined=["dot"])
    assert achievements.job_flags(C, ["dot", "vic", "mabel", "pip", "gus"], out2) == []


def test_the_first_finished_job_earns_first_job_in_the_view_and_the_save(g):
    view = play(g, bots.greedy_plan)
    assert [a["id"] for a in view["achievements"] if a["earned"]][0] == "first_job"
    state = g.module.get_state()
    assert "first_job" in state["achievements_earned"]


def test_achievements_earned_is_never_read_back(g):
    g.module.load_state({"achievements_earned": ["rich_and_infamous", "first_job"], "career_seed": 3})
    assert [a for a in g(action="open")["view"]["achievements"] if a["earned"]] == []


def test_a_real_playthrough_earns_flags_and_the_cat(g):
    for seed in range(30):
        g(action="new_career", seed=seed + 1)
        g.module.career.meta["reputation"] = 30
        for tid in g.module.C.target_order:
            g.module.career.jobs_started = next(n for n in range(400) if tid in g.module._board_targets_for(n))
            view = play(g, bots.greedy_plan, crew=("dot", "pip", "bea", "tomasz", "hank"), target=tid)
            g(action="back_to_board")
        if g.module.career.meta["flags"]:
            break
    assert "full_house" in g.module.career.meta["flags"]
    assert view["phase"] == "payout"


def test_flags_and_cat_targets_survive_a_save(g):
    g.module.career.meta["flags"] = ["full_house"]
    g.module.career.meta["cat_targets"] = ["pigeon_museum"]
    data = json.loads(json.dumps(g.module.get_state()))
    g.module.load_state(data)
    assert g.module.career.meta["flags"] == ["full_house"] and g.module.career.meta["cat_targets"] == ["pigeon_museum"]
    g.module.load_state({"meta": {"flags": ["hacker", "full_house"], "cat_targets": ["nope"]}})
    assert g.module.career.meta["flags"] == ["full_house"] and g.module.career.meta["cat_targets"] == []


# --- story ---------------------------------------------------------------------------------------
def test_minutes_unlock_by_jobs_done():
    assert len(story.minutes({"jobs_done": 0})["entries"]) == 1
    assert len(story.minutes({"jobs_done": 1})["entries"]) == 2
    assert story.minutes({"jobs_done": 99})["next_at"] is None
    assert story.minutes({"jobs_done": 0})["next_at"] == 1


def test_story_text_has_no_placeholders_or_banned_style():
    text = " ".join(t for _n, _h, t in story.MINUTES) + " ".join(story.TRAIT_LINES.values())
    assert "{" not in text and " - " not in text and "!" not in text


def test_every_trait_line_belongs_to_a_real_trait(C):
    assert set(story.TRAIT_LINES) <= set(C.traits)
    assert set(C.traits) - set(story.TRAIT_LINES) == set()


def test_debrief_is_deterministic_and_short(C):
    crew = ["dot", "pip", "bea", "tomasz", "hank"]
    r = engine.simulate(C, "pigeon_museum", crew, bots.greedy_plan(C, "pigeon_museum", crew), seed=5)
    a = story.debrief(C, crew, r, "clean", 5)
    assert a == story.debrief(C, crew, r, "clean", 5) and 2 <= len(a) <= 5
    assert all(d["who"] in {C.crew[c]["short"] for c in crew} for d in a)


def test_the_debrief_never_appears_in_a_mechanical_line(g):
    view = play(g, bots.greedy_plan)
    assert view["payout"]["debrief"]
    for ev in view["playback"]["events"]:
        for d in view["payout"]["debrief"]:
            assert d["text"] not in ev["text"] and d["text"] not in ev["why"]


def test_story_selectors_cover_every_story_element():
    html = (GAME / "index.html").read_text(encoding="utf-8")
    selectors = re.search(r'data-story-selectors="([^"]+)"', html).group(1)
    assert ".ev-flavor" in selectors and "#minutes-panel" in selectors and ".story-line" in selectors
    css_ids = set(re.findall(r'(?<![\w-])id="([^"]+)"', html))
    for sel in selectors.split(","):
        sel = sel.strip()
        if sel.startswith("#"):
            assert sel[1:] in css_ids
