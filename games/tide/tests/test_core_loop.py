"""Milestone 1: core settlement loop — funds, three investment
categories, seasonal round progression. No acidity/sea-level yet."""


def test_initial_state(game_env):
    assert game_env.state.season == 1
    assert game_env.state.funds == 300
    assert all(count == 0 for count in game_env.state.capacity.values())


def test_invest_in_output_deducts_cost_and_increments_capacity(game_env):
    game_env.invest("output")
    assert game_env.state.capacity["output"] == 1
    assert game_env.state.funds == 300 - 20


def test_invest_in_reduction_uses_its_own_cost(game_env):
    game_env.invest("reduction")
    assert game_env.state.capacity["reduction"] == 1
    assert game_env.state.funds == 300 - 25


def test_invest_in_adaptation_uses_its_own_cost(game_env):
    game_env.invest("adaptation")
    assert game_env.state.capacity["adaptation"] == 1
    assert game_env.state.funds == 300 - 30


def test_invest_fails_when_insufficient_funds(game_env):
    game_env.state.funds = 5
    game_env.invest("output")
    assert game_env.state.capacity["output"] == 0
    assert game_env.state.funds == 5


def test_invest_button_disabled_when_unaffordable(game_env):
    game_env.state.funds = 5
    game_env.module.render()
    assert game_env.elements["output-invest-button"].disabled is True


def test_invest_button_enabled_when_affordable(game_env):
    assert game_env.elements["output-invest-button"].disabled is False


def test_advance_season_increments_season_number(game_env):
    game_env.advance_season()
    assert game_env.state.season == 2


def test_advance_season_grants_income_from_output_capacity(game_env):
    game_env.invest("output")
    funds_before = game_env.state.funds
    game_env.advance_season()
    assert game_env.state.funds == funds_before + 6


def test_advance_season_with_no_output_grants_no_income(game_env):
    funds_before = game_env.state.funds
    game_env.advance_season()
    assert game_env.state.funds == funds_before


def test_multiple_seasons_compound_output_income(game_env):
    game_env.invest("output")
    game_env.invest("output")
    funds_before = game_env.state.funds
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.funds == funds_before + 2 * (2 * 6)


def test_render_updates_status_displays(game_env):
    game_env.invest("output")
    game_env.advance_season()
    assert game_env.elements["season-display"].innerText == "Season 2"
    assert "286" in game_env.elements["funds-display"].innerText


def test_render_shows_investment_counts(game_env):
    game_env.invest("reduction")
    game_env.invest("reduction")
    assert game_env.elements["reduction-count"].innerText == "2"
