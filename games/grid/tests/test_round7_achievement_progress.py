"""Round-7 pass: progress readouts on the remaining countable achievements, and the next milestone (C-18)."""
from .test_career import _play


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def test_every_countable_achievement_now_has_a_readout(game_env):
    g = game_env.module
    without = {e["id"] for e in g.ACHIEVEMENTS} - set(g.ACHIEVEMENT_PROGRESS)
    assert without == {"first_watt", "renewable_pioneer", "first_storage"}  # one-step builds stay plain
    assert len(g.ACHIEVEMENT_PROGRESS) == 14


def test_fully_renewable_counts_the_clean_share(game_env):
    g = game_env.module
    assert g.ACHIEVEMENT_PROGRESS["fully_renewable"]() == (0, 100)
    s = game_env.state
    s.plant_counts.update({"coal": 1, "solar": 2})  # 20 coal of 40
    assert g.ACHIEVEMENT_PROGRESS["fully_renewable"]() == (50, 100)
    s.plant_counts["coal"] = 0
    assert g.ACHIEVEMENT_PROGRESS["fully_renewable"]() == (100, 100)


def test_learning_curve_readout_climbs_to_the_floor(game_env):
    g = game_env.module
    s = game_env.state
    assert g.ACHIEVEMENT_PROGRESS["learning_curve_floored"]() == (0, 100)
    s.cumulative_built["wind"] = 9
    mid = g.ACHIEVEMENT_PROGRESS["learning_curve_floored"]()[0]
    assert 30 < mid < 70
    s.cumulative_built["wind"] = 60
    assert g.ACHIEVEMENT_PROGRESS["learning_curve_floored"]() == (100, 100)
    assert "learning_curve_floored" in g.achievement_ids_earned()


def test_learning_curve_readout_ignores_policy_discounts(game_env):
    g = game_env.module
    s = game_env.state
    s.active_policy = {"type": "renewable_subsidy", "rounds_remaining": 3}
    assert g.ACHIEVEMENT_PROGRESS["learning_curve_floored"]() == (0, 100)


def test_fossil_phase_out_has_two_stages(game_env):
    g = game_env.module
    s = game_env.state
    s.funds = 100000
    for _ in range(2):
        game_env.build("coal")
    assert g.ACHIEVEMENT_PROGRESS["fossil_phase_out"]() == (2, 3)
    game_env.build("gas")
    game_env.build("gas")  # 4 built, 4 standing: nothing retired yet
    assert g.ACHIEVEMENT_PROGRESS["fossil_phase_out"]() == (0, 4)
    s.plant_counts["coal"] -= 1  # retire one
    s.plant_counts["gas"] -= 1
    assert g.ACHIEVEMENT_PROGRESS["fossil_phase_out"]() == (2, 4)


def test_no_damage_counts_rounds_and_stops_after_a_damage_event(game_env):
    g = game_env.module
    _play(game_env, 4)
    assert g.ACHIEVEMENT_PROGRESS["no_damage_20"]() == (5, 21)
    game_env.state.event_log.append({"type": "damage"})
    assert g.ACHIEVEMENT_PROGRESS["no_damage_20"]() is None


def test_ahead_of_the_curve_counts_rounds_until_round_eleven(game_env):
    g = game_env.module
    _play(game_env, 3)
    assert g.ACHIEVEMENT_PROGRESS["ahead_of_the_curve"]() == (4, 11)
    _play(game_env, 8)
    assert g.ACHIEVEMENT_PROGRESS["ahead_of_the_curve"]() is None


def test_the_summary_tolerates_readouts_that_return_none(game_env):
    g = game_env.module
    game_env.state.event_log.append({"type": "damage"})
    entry = next(e for e in g.achievements_summary() if e["id"] == "no_damage_20")
    assert entry["progress"] is None


def test_next_milestone_is_the_furthest_along_locked_one(game_env):
    g = game_env.module
    assert g.next_milestone() is None or g.next_milestone()["progress"][0] > 0
    s = game_env.state
    s.plant_counts.update({"coal": 1, "solar": 1})  # 50% renewable of 30 capacity? solar 10 of 30 -> 33%
    upcoming = g.next_milestone()
    assert upcoming is not None and not upcoming["earned"]
    cur, tgt = upcoming["progress"]
    for entry in g.achievements_summary():
        if not entry["earned"] and entry["progress"] and 0 < entry["progress"][0] < entry["progress"][1]:
            assert cur / tgt >= entry["progress"][0] / entry["progress"][1] - 1e-9


def test_next_milestone_is_none_when_nothing_is_started(game_env):
    game_env.state.round_number = 30  # no round-count readouts left, nothing built
    assert game_env.module.next_milestone() is None


def test_panel_shows_the_next_milestone_line_first(game_env):
    g = game_env.module
    game_env.state.plant_counts.update({"coal": 1, "solar": 2})
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    first = panel.children[0]
    assert first.className == "achievement-next" and first.innerText.startswith("Next milestone: ")
    assert any("of" in t for t in _texts(panel))
    assert g.next_milestone()["label"] in first.innerText
