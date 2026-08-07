"""Milestone 1: core farm loop — herd growth, income, round progression.
No methane meter or decoupling yet.
"""


def test_initial_state(game_env):
    assert game_env.farm.round_number == 1
    assert game_env.farm.funds == 300
    assert game_env.farm.herd_size == 0


def test_grow_herd_deducts_cost_and_increments_size(game_env):
    game_env.grow_herd()
    assert game_env.farm.herd_size == 1
    assert game_env.farm.funds == 300 - 20


def test_grow_herd_fails_when_insufficient_funds(game_env):
    game_env.farm.funds = 5
    game_env.grow_herd()
    assert game_env.farm.herd_size == 0
    assert game_env.farm.funds == 5


def test_grow_button_disabled_when_unaffordable(game_env):
    game_env.farm.funds = 5
    game_env.module.render()
    assert game_env.elements["grow-herd-button"].disabled is True


def test_grow_button_enabled_when_affordable(game_env):
    assert game_env.elements["grow-herd-button"].disabled is False


def test_advance_round_increments_round_number(game_env):
    game_env.advance_round()
    assert game_env.farm.round_number == 2


def test_advance_round_grants_income_from_herd_size(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    funds_before = game_env.farm.funds
    game_env.advance_round()
    assert game_env.farm.funds == funds_before + 2 * 5


def test_advance_round_with_no_herd_grants_no_income(game_env):
    funds_before = game_env.farm.funds
    game_env.advance_round()
    assert game_env.farm.funds == funds_before


def test_multiple_rounds_compound_income(game_env):
    game_env.grow_herd()
    funds_before = game_env.farm.funds
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.farm.funds == funds_before + 2 * 5


def test_render_updates_status_displays(game_env):
    game_env.grow_herd()
    game_env.advance_round()
    assert game_env.elements["round-display"].innerText == "Round 2"
    assert game_env.elements["herd-display"].innerText == "Herd size: 1"
    assert "285" in game_env.elements["funds-display"].innerText
