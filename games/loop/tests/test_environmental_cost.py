"""Milestone 3: environmental cost meter — cumulative new extraction
leaves lasting damage that drives up the cost of further extraction. No
hard fail-state: the multiplier is capped, never blocks play outright.
"""

import pytest


def test_damage_starts_at_zero(game_env):
    assert game_env.chain.damage_fraction() == 0.0


def test_cost_multiplier_starts_at_one(game_env):
    assert game_env.chain.extraction_cost_multiplier() == pytest.approx(1.0)


def test_damage_rises_with_cumulative_extraction(game_env):
    game_env.chain.advance_cycle()
    assert game_env.chain.total_extracted == 50.0
    assert game_env.chain.damage_fraction() == pytest.approx(50.0 / 500.0)


def test_damage_accumulates_across_cycles(game_env):
    for _ in range(5):
        game_env.chain.advance_cycle()
    assert game_env.chain.total_extracted == 250.0
    assert game_env.chain.damage_fraction() == pytest.approx(0.5)


def test_damage_fraction_caps_at_one(game_env):
    game_env.chain.total_extracted = 5000.0
    assert game_env.chain.damage_fraction() == 1.0


def test_cost_multiplier_scales_with_damage(game_env):
    game_env.chain.total_extracted = 250.0  # 50% damage
    # 1.0 + 0.5 * (2.5 - 1.0) = 1.75
    assert game_env.chain.extraction_cost_multiplier() == pytest.approx(1.75)


def test_cost_multiplier_caps_at_max(game_env):
    game_env.chain.total_extracted = 5000.0
    assert game_env.chain.extraction_cost_multiplier() == pytest.approx(2.5)


def test_advance_cycle_applies_rising_cost_multiplier(game_env):
    # Rack up damage first via cheap early cycles, then measure a cycle
    # against the now-elevated multiplier.
    for _ in range(5):
        game_env.chain.advance_cycle()
    multiplier_before = game_env.chain.extraction_cost_multiplier()
    assert multiplier_before > 1.0

    funds_before = game_env.chain.funds
    game_env.chain.advance_cycle()
    extraction = 50.0
    expected_cost = extraction * 2.0 * multiplier_before
    expected_revenue = 50.0 * 5.0
    assert game_env.chain.funds == pytest.approx(
        funds_before + expected_revenue - expected_cost
    )


def test_circularity_investment_avoids_feeding_damage(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    for _ in range(5):
        game_env.chain.advance_cycle()
    # Loop fully closed -> no new extraction -> damage never accumulates
    assert game_env.chain.total_extracted == 0.0
    assert game_env.chain.damage_fraction() == 0.0
    assert game_env.chain.extraction_cost_multiplier() == pytest.approx(1.0)


def test_render_shows_damage_display(game_env):
    game_env.chain.advance_cycle()
    game_env.module.render()
    assert "Environmental damage" in game_env.elements["damage-display"].innerText


def test_render_updates_damage_bar_width(game_env):
    game_env.chain.total_extracted = 250.0
    game_env.module.render()
    assert game_env.elements["damage-bar"].style.width == "50%"
