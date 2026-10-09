"""E-29: the 'Helps against' line under every locked skill."""

import pytest


def _text(game_env, skill_id):
    return game_env.elements[f"skill-{skill_id}-helps"].innerText


def test_every_skill_row_has_a_line_and_locked_ones_are_not_empty(game_env):
    m = game_env.module
    for skill_id in m.SKILLS:
        assert _text(game_env, skill_id), skill_id


def test_weather_skill_names_the_remaining_weather_events_with_counts(game_env):
    text = _text(game_env, "climate_hardening")
    # Classic: flood, heatwave, storm, flood -> Flood x2, Heatwave, Storm
    assert "Flood ×2" in text and "Heatwave" in text and "Storm" in text
    assert "Civil Unrest" not in text and "Supply" not in text


def test_social_skill_only_names_civil_unrest(game_env):
    text = _text(game_env, "civic_preparedness")
    assert "Civil Unrest" in text and "Flood" not in text


def test_general_skill_names_every_remaining_event_and_the_exact_saving(game_env):
    m = game_env.module
    counts, saved = m.skill_helps_against("early_warning")
    assert sum(counts.values()) == 7
    expected = sum(m.EVENT_BASE_DAMAGE[t] for t in m.run.schedule) * 0.10  # run 1 severity is 1.0, no cap reached
    assert saved == pytest.approx(expected)
    assert f"About {saved:.0f} less damage" in _text(game_env, "early_warning")


def test_events_already_faced_drop_out_of_the_line(game_env):
    m = game_env.module
    game_env.resolve_event()  # a flood
    counts, _ = m.skill_helps_against("climate_hardening")
    assert counts["Flood"] == 1
    for _ in range(6):
        game_env.resolve_event()
    assert m.run.is_complete()
    assert "next run" in _text(game_env, "climate_hardening")


def test_a_skill_with_nothing_left_to_soften_says_so(game_env):
    m = game_env.module
    m.run = m.RunState(scenario="urban")
    m.run.event_index = 6  # only civil unrest is left
    m.render()
    text = _text(game_env, "climate_hardening")
    assert "nothing left" in text


def test_cap_limits_the_saving(game_env):
    m = game_env.module
    m.run.resilience_capacity = 17  # 85% already
    counts, saved = m.skill_helps_against("early_warning")
    assert saved == 0.0 and sum(counts.values()) == 7


def test_starting_build_skills_say_they_help_from_the_next_run(game_env):
    for skill_id in ("reinforced_infrastructure", "community_reserves", "adaptive_growth"):
        assert "next run" in _text(game_env, skill_id)
    assert "+56" in _text(game_env, "adaptive_growth")


def test_unlocked_skills_show_no_line(game_env):
    m = game_env.module
    m.skill_tree.unlocked.add("early_warning")
    m.render()
    assert _text(game_env, "early_warning") == ""


def test_the_line_follows_the_scenario(game_env):
    game_env.elements["scenario-select"].value = "heat_season"
    game_env.elements["scenario-select"].dispatch("change", None)
    assert "Heat-Health" not in _text(game_env, "climate_hardening")  # health is not weather
    assert "Heatwave" in _text(game_env, "climate_hardening")
