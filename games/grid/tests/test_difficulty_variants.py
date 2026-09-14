"""C16/C4: opt-in difficulty variants -- "steeper demand growth" and
"weather variability on renewable output". Both off by default, both
separate knobs from the emissions-driven disruption curve (CLAUDE.md's
Pass 3 note) -- toggling either must never change disruption
probability/severity math."""

import pytest

NEVER_TRIGGER = lambda: 0.999999


def test_off_by_default(game_env):
    assert game_env.state.steeper_demand_growth_enabled is False


def test_normal_demand_growth_when_disabled(game_env):
    state = game_env.state
    demand_before = state.demand
    state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert state.demand == demand_before + game_env.module.DEMAND_GROWTH_PER_ROUND


def test_steeper_demand_growth_once_enabled(game_env):
    state = game_env.state
    state.steeper_demand_growth_enabled = True
    demand_before = state.demand
    state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    expected_growth = game_env.module.DEMAND_GROWTH_PER_ROUND * game_env.module.STEEP_DEMAND_GROWTH_MULTIPLIER
    assert state.demand == demand_before + expected_growth


def test_toggle_button_flips_the_setting(game_env):
    assert game_env.state.steeper_demand_growth_enabled is False
    game_env.toggle_steeper_demand()
    assert game_env.state.steeper_demand_growth_enabled is True
    game_env.toggle_steeper_demand()
    assert game_env.state.steeper_demand_growth_enabled is False


def test_toggle_button_text_reflects_state(game_env):
    game_env.toggle_steeper_demand()
    assert "ON" in game_env.elements["steeper-demand-toggle-button"].innerText
    game_env.toggle_steeper_demand()
    assert "OFF" in game_env.elements["steeper-demand-toggle-button"].innerText


def test_steeper_demand_growth_does_not_affect_disruption_math(game_env):
    """The whole point of keeping this a separate knob: it must not touch
    the emissions-driven curve at all."""
    state = game_env.state
    state.emissions = 1000.0
    probability_before = state.disruption_probability()
    severity_before = state.disruption_severity()
    state.steeper_demand_growth_enabled = True
    assert state.disruption_probability() == probability_before
    assert state.disruption_severity() == severity_before


def test_setting_round_trips_through_save_load(game_env):
    module = game_env.module
    game_env.toggle_steeper_demand()
    snapshot = module.get_state()
    assert snapshot["steeper_demand_growth_enabled"] is True

    game_env.toggle_steeper_demand()  # diverge
    module.load_state(snapshot)
    assert module.state.steeper_demand_growth_enabled is True


# --- C4: opt-in weather variability on renewable output -----------------

def test_weather_variability_off_by_default(game_env):
    assert game_env.state.weather_variability_enabled is False


def test_effective_capacity_equals_total_capacity_when_disabled(game_env):
    game_env.build("coal")
    game_env.build("solar")
    assert game_env.state.effective_capacity_for_revenue() == game_env.state.total_capacity()


def test_effective_capacity_scales_only_renewables_when_enabled(game_env):
    state = game_env.state
    game_env.build("coal")  # 20 cap, dispatchable -- unaffected
    game_env.build("solar")  # 10 cap, renewable -- affected
    state.weather_variability_enabled = True

    # A "high wind/sun" roll (rng() -> 1.0) pushes the factor to its max:
    # 1 + (1*2-1)*0.2 = 1.2
    high_roll = lambda: 1.0
    effective = state.effective_capacity_for_revenue(weather_rng=high_roll)
    assert effective == pytest.approx(20 + 10 * 1.2)

    # A "low wind/sun" roll (rng() -> 0.0) pushes the factor to its min:
    # 1 + (0*2-1)*0.2 = 0.8
    low_roll = lambda: 0.0
    effective = state.effective_capacity_for_revenue(weather_rng=low_roll)
    assert effective == pytest.approx(20 + 10 * 0.8)


def test_weather_variability_does_not_change_installed_total_capacity(game_env):
    """total_capacity() (used for cost/display elsewhere) must stay the
    nameplate figure -- variance only affects actual output for revenue,
    never what's "installed"."""
    game_env.build("solar")
    game_env.state.weather_variability_enabled = True
    before = game_env.state.total_capacity()
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER, weather_rng=lambda: 0.0)
    assert game_env.state.total_capacity() == before


def test_weather_variability_does_not_change_emissions(game_env):
    """Emissions are a function of nameplate capacity (emissions_this_round()
    reads plant_counts/PLANT_CAPACITY directly), not this round's weather-
    adjusted output -- coal is dispatchable and unaffected by weather
    variability anyway, but this pins that emissions math never routes
    through effective_capacity_for_revenue() at all."""
    game_env.build("coal")
    without_weather = game_env.state.emissions_this_round()
    game_env.state.weather_variability_enabled = True
    with_weather = game_env.state.emissions_this_round()
    assert without_weather == with_weather


def test_weather_variability_does_not_affect_disruption_math(game_env):
    state = game_env.state
    state.emissions = 1000.0
    probability_before = state.disruption_probability()
    state.weather_variability_enabled = True
    assert state.disruption_probability() == probability_before


def test_weather_toggle_button_flips_the_setting(game_env):
    assert game_env.state.weather_variability_enabled is False
    game_env.toggle_weather_variability()
    assert game_env.state.weather_variability_enabled is True


def test_weather_setting_round_trips_through_save_load(game_env):
    module = game_env.module
    game_env.toggle_weather_variability()
    snapshot = module.get_state()
    assert snapshot["weather_variability_enabled"] is True

    game_env.toggle_weather_variability()  # diverge
    module.load_state(snapshot)
    assert module.state.weather_variability_enabled is True
