"""Round-7 pass: the opt-in coach (C-21)."""
from .test_round7_trend import _tick


def _coach(game_env):
    game_env.module.render()
    return game_env.elements["coach-text"].innerText


def test_coach_is_off_by_default_and_hidden(game_env):
    game_env.module.render()
    assert game_env.module.prefs["coach"] is False
    assert game_env.elements["coach-panel"].hidden is True
    assert game_env.elements["coach-text"].innerText == ""


def test_checkbox_turns_the_coach_on_and_off(game_env):
    _tick(game_env, "pref-coach", True)
    assert game_env.elements["coach-panel"].hidden is False
    assert "no generation yet" in game_env.elements["coach-text"].innerText
    _tick(game_env, "pref-coach", False)
    assert game_env.elements["coach-panel"].hidden is True


def test_empty_grid_points_at_the_cheapest_capacity(game_env):
    game_env.module.prefs["coach"] = True
    text = _coach(game_env)
    assert "no generation yet" in text and "for the price" in text


def test_short_of_demand_says_how_short(game_env):
    game_env.module.prefs["coach"] = True
    game_env.state.plant_counts["coal"] = 2  # 40 capacity against demand 100
    text = _coach(game_env)
    assert "60 short of demand 100" in text and "more" in text


def test_aging_risk_names_the_fleet_and_the_maintenance_price(game_env):
    game_env.module.prefs["coach"] = True
    s = game_env.state
    s.plant_counts["coal"] = 8
    s.plant_age["coal"] = 20.0
    text = _coach(game_env)
    assert "Coal fleet" in text and "worn" in text and f"{s.maintenance_cost('coal'):.0f}" in text


def test_disruption_risk_line_names_the_source(game_env):
    g = game_env.module
    g.prefs["coach"] = True
    s = game_env.state
    s.plant_counts["coal"] = 6
    s.emissions = 900.0
    assert s.disruption_probability() >= g.COACH_DISRUPTION_THRESHOLD
    text = _coach(game_env)
    assert "chance of a disruption" in text and "Coal" in text


def test_growing_demand_warning(game_env):
    game_env.module.prefs["coach"] = True
    s = game_env.state
    s.plant_counts["nuclear"] = 1  # exactly 100 capacity for demand 100
    text = _coach(game_env)
    assert "rises to 110 next round" in text


def test_idle_funds_suggest_the_cheapest_renewable(game_env):
    game_env.module.prefs["coach"] = True
    s = game_env.state
    s.plant_counts["nuclear"] = 2
    s.plant_counts["coal"] = 1
    s.funds = 5000
    text = _coach(game_env)
    assert "holding 5000 funds" in text and "keeps getting cheaper" in text


def test_battery_hint_needs_weather_variability_and_renewables(game_env):
    g = game_env.module
    g.prefs["coach"] = True
    s = game_env.state
    s.plant_counts["hydro"] = 5  # 200 capacity, all renewable
    s.funds = 10
    s.weather_variability_enabled = True
    assert "battery" in _coach(game_env).lower()
    s.plant_counts["battery"] = 1
    assert "battery" not in _coach(game_env).lower()


def test_nothing_urgent_when_all_is_well(game_env):
    game_env.module.prefs["coach"] = True
    s = game_env.state
    s.plant_counts["nuclear"] = 3  # 300 capacity, no emissions
    s.funds = 10
    assert _coach(game_env).startswith("Nothing urgent")


def test_coach_never_changes_state_or_the_save(game_env):
    g = game_env.module
    before = g.get_state()
    g.prefs["coach"] = True
    g.render()
    g.coach_observation()
    assert g.get_state() == before


def test_coach_text_is_one_short_line(game_env):
    g = game_env.module
    s = game_env.state
    for setup in (lambda: None, lambda: s.plant_counts.update({"coal": 2}), lambda: s.plant_age.update({"coal": 30.0})):
        setup()
        assert "\n" not in g.coach_observation() and len(g.coach_observation()) < 260


def test_settings_reset_puts_every_display_choice_back(game_env):
    g = game_env.module
    g.set_pref("coach", True)
    g.set_pref("trend_funds", True)
    g.set_pref("unit", "mw")
    game_env.elements["settings-reset-button"].dispatch("click", None)
    assert g.prefs == g.PREF_DEFAULTS
    assert game_env.elements["coach-panel"].hidden is True
