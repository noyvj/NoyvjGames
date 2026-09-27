"""GB-22: standing value tiers (1k Seedling, 2.5k Grove, 5k Woodland, 10k
Old-Growth) with a title bump and light pulse; the higher tiers are also achievements."""

import json
from pathlib import Path

from .gb_helpers import log_kinds, toast_text

HERE = Path(__file__).resolve().parent.parent


def _set_value(m, total):
    for plot in m.plots:
        plot.value = 0.0
    m.plots[0].value = total


def test_tier_table_matches_the_idea(game_env):
    m = game_env.module
    assert m.STANDING_TIERS == [(1000.0, "Seedling"), (2500.0, "Grove"), (5000.0, "Woodland"), (10000.0, "Old-Growth")]


def test_no_title_before_the_first_tier(game_env):
    m = game_env.module
    game_env.tick(3)
    assert m.forest_title() == ""
    assert game_env.elements["forest-title-display"].hidden is True


def test_first_tier_gives_a_title_toast_log_and_pulse(game_env):
    m = game_env.module
    _set_value(m, 1000.0)
    game_env.tick()
    assert m.milestone_tier == 1 and m.forest_title() == "Seedling"
    assert "Seedling" in game_env.elements["forest-title-display"].innerText
    assert "Seedling" in toast_text(game_env)
    assert "milestone" in log_kinds(m)
    visual = game_env.elements["forest-visual"]
    assert visual.classList.contains("forest-pulse")
    assert game_env.elements["forest-title-display"].classList.contains("just-improved")
    game_env.timers.flush()
    assert not visual.classList.contains("forest-pulse")
    assert not game_env.elements["forest-title-display"].classList.contains("just-improved")


def test_each_tier_fires_once_in_order(game_env):
    m = game_env.module
    titles = []
    for value in (1000.0, 2500.0, 5000.0, 10000.0):
        _set_value(m, value)
        game_env.tick()
        titles.append(m.forest_title())
    assert titles == ["Seedling", "Grove", "Woodland", "Old-Growth"]
    before = len(m.forest_log)
    game_env.tick(3)
    assert [e["kind"] for e in m.forest_log[before:]].count("milestone") == 0


def test_jumping_several_tiers_logs_each_and_celebrates_the_highest(game_env):
    m = game_env.module
    _set_value(m, 6000.0)
    game_env.tick()
    assert m.milestone_tier == 3
    assert log_kinds(m).count("milestone") == 3
    assert "Woodland" in toast_text(game_env)


def test_the_title_survives_clearing_the_forest(game_env):
    m = game_env.module
    _set_value(m, 2600.0)
    game_env.tick()
    _set_value(m, 0.0)
    game_env.tick()
    assert m.forest_title() == "Grove" and m.milestone_tier == 2


def test_forest_name_is_shown_with_the_title(game_env):
    m = game_env.module
    m.set_forest_name("Wren Hollow")
    _set_value(m, 1100.0)
    game_env.tick()
    assert "Wren Hollow" in game_env.elements["forest-title-display"].innerText
    assert any("Wren Hollow grew into a Seedling forest" in e["text"] for e in m.forest_log)


def test_new_achievements_exist_with_labels_and_chapters():
    ids = ("tier_grove", "tier_woodland", "tier_old_growth_steward")
    achievements = {a["id"]: a for a in json.loads((HERE / "achievements.json").read_text())["achievements"]}
    chapters = {c["id"]: c for c in json.loads((HERE / "story.json").read_text())["chapters"]}
    for achievement_id in ids:
        assert achievements[achievement_id]["label"] and achievements[achievement_id]["description"]
        assert len(chapters[achievement_id]["text"]) >= 60 and not any(ch.isdigit() for ch in chapters[achievement_id]["text"])
    assert "standing_fortune" in achievements  # the 1,000 tier already had one
    assert len(achievements) == 24


def test_achievements_are_earned_at_2500_5000_and_10000(game_env):
    m = game_env.module
    for value, earned in ((2400.0, []), (2600.0, ["tier_grove"]),
                          (5100.0, ["tier_grove", "tier_woodland"]),
                          (10100.0, ["tier_grove", "tier_woodland", "tier_old_growth_steward"])):
        _set_value(m, value)
        game_env.tick()
        got = [i for i in m.achievement_ids_earned() if i.startswith("tier_")]
        assert got == earned


def test_tier_achievements_are_sticky_after_clearing(game_env):
    m = game_env.module
    _set_value(m, 2600.0)
    game_env.tick()
    _set_value(m, 0.0)
    assert "tier_grove" in m.achievement_ids_earned()


def test_tier_achievements_have_progress_and_a_story_link(game_env):
    m = game_env.module
    _set_value(m, 1250.0)
    game_env.tick()
    summary = {a["id"]: a for a in m.achievements_summary()}
    current, target = summary["tier_grove"]["progress"]
    assert target == 2500 and 1250 <= current < 1400
    assert m.ACHIEVEMENTS and len(m.ACHIEVEMENTS) == 24


def test_save_round_trip_and_older_saves_do_not_celebrate(game_env):
    m = game_env.module
    assert "peak_standing_value" not in m.get_state() and "milestone_tier" not in m.get_state()
    _set_value(m, 2600.0)
    game_env.tick()
    state = m.get_state()
    assert state["milestone_tier"] == 2 and state["peak_standing_value"] >= 2600
    old = {k: v for k, v in state.items() if k not in ("milestone_tier", "peak_standing_value")}
    game_env.timers.flush()
    game_env.reset_session()
    m.load_state(old)
    assert m.milestone_tier == 2  # derived silently from the value it already had
    assert m._gb_toast_queue == []
    assert not game_env.elements["forest-visual"].classList.contains("forest-pulse")


def test_load_validates_tier_data(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in (True, "9", -3, 99, None, [1], float("nan")):
        m.load_state(dict(base, milestone_tier=bad, peak_standing_value=bad))
        assert 0 <= m.milestone_tier <= 4
        assert m.peak_standing_value >= 0


def test_a_tier_claimed_by_a_tampered_save_is_capped_by_the_real_peak(game_env):
    m = game_env.module
    m.load_state(dict(m.get_state(), milestone_tier=4, peak_standing_value=10.0))
    assert m.milestone_tier == 0


def test_reset_clears_tiers(game_env):
    m = game_env.module
    _set_value(m, 1100.0)
    game_env.tick()
    game_env.reset_session()
    assert m.milestone_tier == 0 and m.peak_standing_value == 0.0
