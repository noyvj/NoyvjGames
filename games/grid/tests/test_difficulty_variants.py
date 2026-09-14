"""C16: an opt-in "steeper demand growth" difficulty variant. Off by
default; a separate knob from the emissions-driven disruption curve
(CLAUDE.md's Pass 3 note) -- toggling it must never change disruption
probability/severity math."""

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
