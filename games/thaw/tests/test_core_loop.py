"""Milestone 1: background trajectory + core loop. Temperature rises on a
fixed schedule regardless of player action — the player isn't the primary
driver of the central meter here, unlike Herd/Grid. No feedback loop yet.
"""


def test_initial_state(game_env):
    assert game_env.region.round_number == 1
    assert game_env.region.funds == 300
    assert game_env.region.temperature == 0.0
    assert all(count == 0 for count in game_env.region.capacity.values())


def test_invest_in_output_deducts_cost_and_increments_capacity(game_env):
    game_env.invest("output")
    assert game_env.region.capacity["output"] == 1
    assert game_env.region.funds == 300 - 20


def test_invest_in_preserve_uses_its_own_cost(game_env):
    game_env.invest("preserve")
    assert game_env.region.capacity["preserve"] == 1
    assert game_env.region.funds == 300 - 25


def test_invest_in_monitor_uses_its_own_cost(game_env):
    game_env.invest("monitor")
    assert game_env.region.capacity["monitor"] == 1
    assert game_env.region.funds == 300 - 20


def test_invest_fails_when_insufficient_funds(game_env):
    game_env.region.funds = 5
    game_env.invest("output")
    assert game_env.region.capacity["output"] == 0
    assert game_env.region.funds == 5


def test_advance_round_increments_round_number(game_env):
    game_env.advance_round()
    assert game_env.region.round_number == 2


def test_temperature_rises_every_round_regardless_of_investment(game_env):
    game_env.advance_round()
    assert game_env.region.temperature == 1.0


def test_temperature_rise_is_identical_with_or_without_investment(game_env):
    for _ in range(5):
        game_env.invest("preserve")
    game_env.advance_round()
    assert game_env.region.temperature == 1.0  # unaffected by investment in M1


def test_temperature_accumulates_across_rounds(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.region.temperature == 3.0


def test_advance_round_grants_income_from_output_capacity(game_env):
    game_env.invest("output")
    funds_before = game_env.region.funds
    game_env.advance_round()
    assert game_env.region.funds == funds_before + 6


def test_render_updates_status_displays(game_env):
    game_env.invest("output")
    game_env.advance_round()
    assert game_env.elements["round-display"].innerText == "Round 2"
    assert "286" in game_env.elements["funds-display"].innerText
    assert "+1.0" in game_env.elements["temperature-display"].innerText
