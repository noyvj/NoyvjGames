import json
from pathlib import Path

import achievements
import progress
from state import FLAGS, new_meta, new_record

GAME_DIR = Path(__file__).resolve().parent.parent
CHAPTERS = [["a1", "a2"], ["b1", "b2"]]


def meta_with(stars=None, flags=(), practice=0):
    m = new_meta()
    for cid, n in (stars or {}).items():
        m["charts"][cid] = dict(new_record(), stars=n)
    m["flags"] = [f for f in FLAGS if f in flags]
    m["practice_seeds_played"] = practice
    return m


def test_there_are_fourteen_achievements_and_the_manifest_matches_the_module():
    assert len(achievements.ACHIEVEMENTS) == 14
    manifest = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [(a["id"], a["label"], a["description"]) for a in manifest] == list(achievements.ACHIEVEMENTS)
    ids = [a[0] for a in achievements.ACHIEVEMENTS]
    assert len(set(ids)) == 14 and set(achievements.FLAG_OF) <= set(ids)
    assert set(achievements.FLAG_OF.values()) <= set(FLAGS)


def test_a_fresh_save_has_earned_nothing():
    assert achievements.earned(new_meta(), CHAPTERS) == []


def test_flag_achievements_follow_their_flags():
    for aid, flag in achievements.FLAG_OF.items():
        assert achievements.earned(meta_with(flags=[flag]), CHAPTERS) == [aid]


def test_chapter_closer_needs_every_chart_of_one_chapter():
    assert "chapter_closer" not in achievements.earned(meta_with({"a1": 1}), CHAPTERS)
    assert "chapter_closer" in achievements.earned(meta_with({"a1": 1, "a2": 1}), CHAPTERS)
    assert "chapter_closer" in achievements.earned(meta_with({"b1": 3, "b2": 1}), CHAPTERS)


def test_practice_makes_counts_ten_practice_charts():
    assert "practice_makes" not in achievements.earned(meta_with(practice=9), CHAPTERS)
    assert "practice_makes" in achievements.earned(meta_with(practice=10), CHAPTERS)


def test_all_stars_needs_three_stars_everywhere():
    full = {"a1": 3, "a2": 3, "b1": 3, "b2": 2}
    assert "all_stars" not in achievements.earned(meta_with(full), CHAPTERS)
    full["b2"] = 3
    assert "all_stars" in achievements.earned(meta_with(full), CHAPTERS)


def test_view_lists_all_with_earned_marks():
    v = achievements.view(meta_with(flags=["landfall"]), CHAPTERS)
    assert len(v) == 14 and [a["id"] for a in v if a["earned"]] == ["first_landfall"]


def test_the_saved_projection_is_written_and_never_read_back(g):
    assert "achievements_earned" not in g.get_state()
    g.meta["flags"] = ["landfall"]
    assert g.get_state()["achievements_earned"] == ["first_landfall"]
    g.call("reset")
    g.load_state({"achievements_earned": ["all_stars", "aground"]})
    assert g.get_state() == {"schema": 1}                      # nothing was believed from the blob


def test_the_view_carries_the_list_for_the_panel(g):
    v = g.call("open")
    assert len(v["achievements"]) == 14 and not any(a["earned"] for a in v["achievements"])


def play_par(g, cid, mode="plan"):
    g.call("start", chart_id=cid)
    g.call("set_mode", mode="plan")
    for leg in g.charts.par_legs(cid):
        n = len(g.call("add_leg")["legs"])
        g.call("set_leg", i=n - 1, **leg)
    return g.call("sail")


def test_the_whole_game_can_be_one_hundred_percented_with_the_par_plans(g):
    """Easy to 100%: sail every authored par plan, take a fix once, run aground once and sail ten practice charts."""
    # open every chapter first so the par plans can be started in any order
    for cid in g.charts.ORDER[:12]:
        g.meta["charts"][cid] = dict(new_record(), stars=1)
    for cid in g.charts.ORDER:
        v = play_par(g, cid)
        assert v["reveal"]["stars"] == 3, (cid, v["reveal"]["criteria"])
    assert "trusted" in g.meta["flags"]
    # a watch passage with a fix
    g.call("start", chart_id="fix-01")
    g.call("add_leg")
    g.call("set_leg", i=0, heading=44, hours=2.0)
    g.call("sail")
    g.call("take_fix", landmark="cape-light")
    g.call("anchor")
    # one grounding
    g.call("start", chart_id="open-02")
    g.call("add_leg")
    g.call("set_leg", i=0, heading=90, speed=5, hours=3.0)
    assert g.call("sail")["reveal"]["aground"]
    for k in range(10):
        g.call("practice", difficulty=1, seed=100 + k)
        g.call("add_leg")
        g.call("sail")
    earned = {a["id"] for a in g.call("open")["achievements"] if a["earned"]}
    missing = {a[0] for a in achievements.ACHIEVEMENTS} - earned
    assert not missing, missing


def test_dead_on_is_reachable_a_plot_that_matches_the_truth_within_half_a_mile(g):
    got = False
    for cid in g.charts.ORDER:
        g.meta["charts"][cid] = dict(new_record(), stars=1)
    g.meta["flags"] = []
    for cid in ("open-01", "open-02", "wind-01", "comp-01"):
        play_par(g, cid)
        got = got or "dead_on" in g.meta["flags"]
    assert got, "the par plans end within half a mile of their own forecast on at least one of these charts"


def test_some_campaign_chart_has_three_hazards_on_the_direct_line(g):
    assert max(progress.hazards_on_the_line(c) for c in g.charts.all_charts()) >= 3
