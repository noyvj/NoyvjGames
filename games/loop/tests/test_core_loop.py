"""Milestone 1: core linear chain — extraction -> manufacturing -> use ->
disposal, a straight line by default. No circularity investment yet, so
every cycle's production target requires 100% new extraction.
"""

import pytest


def test_initial_state(game_env):
    assert game_env.chain.cycle_number == 1
    assert game_env.chain.funds == 300
    assert game_env.chain.total_extracted == 0.0
    assert game_env.chain.total_produced == 0.0


def test_circular_supply_is_zero_by_default(game_env):
    assert game_env.chain.circular_supply() == 0.0


def test_new_extraction_needed_equals_full_production_target(game_env):
    assert game_env.chain.new_extraction_needed() == 50.0


def test_advance_cycle_increments_cycle_number(game_env):
    game_env.advance_cycle()
    assert game_env.chain.cycle_number == 2


def test_advance_cycle_accumulates_total_extraction(game_env):
    game_env.advance_cycle()
    assert game_env.chain.total_extracted == 50.0


def test_advance_cycle_accumulates_total_production(game_env):
    game_env.advance_cycle()
    assert game_env.chain.total_produced == 50.0


def test_multiple_cycles_compound_extraction(game_env):
    game_env.advance_cycle()
    game_env.advance_cycle()
    game_env.advance_cycle()
    assert game_env.chain.total_extracted == 150.0


def test_advance_cycle_updates_funds_by_net_margin(game_env):
    funds_before = game_env.chain.funds
    game_env.advance_cycle()
    # revenue (50*5) - extraction cost (50*2) = 150 net
    assert game_env.chain.funds == pytest.approx(funds_before + 150.0)


def test_render_updates_status_displays(game_env):
    game_env.advance_cycle()
    assert game_env.elements["cycle-display"].innerText == "Cycle 2"
    assert "450" in game_env.elements["funds-display"].innerText
    assert "50" in game_env.elements["total-extracted-display"].innerText
