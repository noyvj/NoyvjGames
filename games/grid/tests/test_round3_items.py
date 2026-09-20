"""Round-3 pass (2026-09-20, planning/TODO.md C7/C17/C19): demand response,
the weather-event log, and the policy lever -- the three "large mechanics"
CLAUDE.md's own round-2 note explicitly left for a later pass."""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


# --- C7: demand response ---------------------------------------------------


def test_demand_response_button_shows_escalating_cost(game_env):
    state = game_env.state
    state.funds = 10_000
    first_cost = state.demand_response_cost()
    assert f"{first_cost:.0f}" in game_env.elements["demand-response-button"].innerText

    game_env.invest_demand_response()
    second_cost = state.demand_response_cost()
    assert second_cost > first_cost
    assert f"{second_cost:.0f}" in game_env.elements["demand-response-button"].innerText


def test_invest_demand_response_spends_funds_and_trims_growth(game_env):
    state = game_env.state
    state.funds = 10_000
    baseline_growth = state.demand_growth_this_round()

    cost = state.demand_response_cost()
    game_env.invest_demand_response()

    assert state.funds == 10_000 - cost
    assert state.demand_response_level == 1
    assert state.demand_growth_this_round() < baseline_growth


def test_demand_response_button_disabled_when_unaffordable(game_env):
    state = game_env.state
    state.funds = 0
    game_env.module.render()
    assert game_env.elements["demand-response-button"].disabled is True


def test_demand_response_cannot_go_below_floor(game_env):
    state = game_env.state
    state.funds = 10 ** 9
    for _ in range(50):
        game_env.invest_demand_response()
    assert state.demand_growth_this_round() == state.demand_growth_this_round()  # no crash
    from game import DEMAND_RESPONSE_MIN_GROWTH

    assert state.demand_growth_this_round() >= DEMAND_RESPONSE_MIN_GROWTH


def test_demand_response_display_updates_once_invested(game_env):
    state = game_env.state
    assert "not yet invested" in game_env.elements["demand-response-level-display"].innerText
    state.funds = 10_000
    game_env.invest_demand_response()
    assert "level: 1" in game_env.elements["demand-response-level-display"].innerText


def test_investing_without_enough_funds_does_nothing(game_env):
    state = game_env.state
    state.funds = 0
    ok = state.invest_demand_response()
    assert ok is False
    assert state.demand_response_level == 0


# --- C17: weather-event log --------------------------------------------


def test_weather_log_empty_until_opened_and_populated(game_env):
    panel = game_env.elements["weather-log-panel"]
    assert panel.hidden is True

    game_env.toggle_weather_log()
    assert panel.hidden is False
    assert any("No weather-variability" in t for t in _all_texts(panel))

    game_env.toggle_weather_log()
    assert panel.hidden is True


def test_weather_log_records_entries_once_renewables_built_and_variability_on(game_env):
    state = game_env.state
    game_env.toggle_weather_variability()
    game_env.build("solar")
    for _ in range(5):
        game_env.advance_round()

    assert len(state.weather_log) > 0
    game_env.toggle_weather_log()
    panel = game_env.elements["weather-log-panel"]
    texts = _all_texts(panel)
    assert any("Round" in t for t in texts)
    assert any("weather variability" in t for t in texts)


def test_weather_log_stays_empty_without_variability_enabled(game_env):
    state = game_env.state
    game_env.build("solar")
    for _ in range(5):
        game_env.advance_round()
    assert state.weather_log == []


def test_weather_log_capped_at_max_entries(game_env):
    state = game_env.state
    game_env.toggle_weather_variability()
    game_env.build("solar")
    for _ in range(60):
        game_env.advance_round()

    from game import WEATHER_LOG_MAX_ENTRIES

    assert len(state.weather_log) <= WEATHER_LOG_MAX_ENTRIES


# --- C19: policy lever ---------------------------------------------------


def test_policy_lever_offered_on_schedule(game_env):
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL

    assert state.policy_lever_available is False
    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    assert state.policy_lever_available is True
    assert game_env.elements["policy-lever-banner"].hidden is False


def test_enacting_carbon_pricing_raises_fossil_cost(game_env):
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL, CARBON_PRICING_FOSSIL_COST_MULTIPLIER

    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    base_coal_cost = state.plant_cost("coal")

    game_env.enact_carbon_pricing()
    assert state.active_policy["type"] == "carbon_pricing"
    assert state.policy_lever_available is False
    assert state.plant_cost("coal") == base_coal_cost * CARBON_PRICING_FOSSIL_COST_MULTIPLIER
    assert "Carbon Pricing" in game_env.elements["active-policy-display"].innerText


def test_enacting_renewable_subsidy_lowers_renewable_cost(game_env):
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL, RENEWABLE_SUBSIDY_COST_MULTIPLIER

    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    base_solar_cost = state.plant_cost("solar")

    game_env.enact_renewable_subsidy()
    assert abs(state.plant_cost("solar") - base_solar_cost * RENEWABLE_SUBSIDY_COST_MULTIPLIER) < 1e-9


def test_policy_expires_after_its_duration(game_env):
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL, POLICY_LEVER_DURATION

    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    game_env.enact_carbon_pricing()

    for _ in range(POLICY_LEVER_DURATION):
        assert state.active_policy is not None
        game_env.advance_round()
    assert state.active_policy is None


def test_declining_policy_clears_the_offer_without_enacting(game_env):
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL

    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    game_env.decline_policy()
    assert state.policy_lever_available is False
    assert state.active_policy is None


def test_retire_refund_ignores_active_policy_multiplier(game_env):
    """plant_cost() (build price) includes the policy multiplier;
    retiring must refund off the un-adjusted learning-curve price, per
    _learning_curve_cost()'s own docstring, so a subsidized-cheap build
    can't be retired for an inflated refund."""
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL, REFUND_FRACTION

    state.funds = 10_000
    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    game_env.enact_renewable_subsidy()

    build_cost = state.plant_cost("solar")
    funds_before_build = state.funds
    game_env.build("solar")
    # Captured *after* building -- cumulative_built just went up, which
    # moves the learning-curve price itself, and retire_plant() reads
    # this fresh at retire time, not the pre-build value.
    learning_curve_cost_at_retire = state._learning_curve_cost("solar")
    game_env.retire("solar")
    assert state.funds == funds_before_build - build_cost + learning_curve_cost_at_retire * REFUND_FRACTION


def test_retire_refund_ignores_active_policy_multiplier_carbon(game_env):
    state = game_env.state
    from game import POLICY_LEVER_INTERVAL, REFUND_FRACTION

    state.funds = 10_000
    for _ in range(POLICY_LEVER_INTERVAL):
        game_env.advance_round()
    game_env.enact_carbon_pricing()

    build_cost = state.plant_cost("coal")
    funds_before_build = state.funds
    game_env.build("coal")
    learning_curve_cost_at_retire = state._learning_curve_cost("coal")
    game_env.retire("coal")
    assert state.funds == funds_before_build - build_cost + learning_curve_cost_at_retire * REFUND_FRACTION
