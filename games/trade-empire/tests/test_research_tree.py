"""Milestone 8: research tree v1. A small, flat framework (no
prerequisites yet) spent from a separate, passively-accruing research-
points currency -- distinct from trade profit -- gating an automation-
slot expansion, a fleet-wide speed boost, and a fleet-wide cargo boost.
"""

import pytest


def test_research_points_start_at_zero(game_env):
    assert game_env.module.research_points == 0.0


def test_research_points_accrue_each_tick(game_env):
    game_env.tick(1)
    assert game_env.module.research_points == game_env.module.RESEARCH_PER_TICK


def test_research_points_are_independent_of_trade_profit(game_env):
    game_env.module.total_profit = 500
    game_env.tick(1)
    assert game_env.module.research_points == game_env.module.RESEARCH_PER_TICK
    assert game_env.module.total_profit == 500  # unaffected by research accrual


def test_cannot_unlock_without_enough_points(game_env):
    result = game_env.module.unlock_research("fast_ships")
    assert result is False
    assert "fast_ships" not in game_env.module.unlocked_research


def test_unlock_succeeds_with_enough_points_and_deducts_cost(game_env):
    game_env.module.research_points = 100
    result = game_env.module.unlock_research("fast_ships")
    assert result is True
    assert "fast_ships" in game_env.module.unlocked_research
    assert game_env.module.research_points == 100 - game_env.module.RESEARCH_NODES["fast_ships"]["cost"]


def test_cannot_unlock_the_same_node_twice(game_env):
    game_env.module.research_points = 100
    game_env.module.unlock_research("fast_ships")
    points_after_first = game_env.module.research_points
    result = game_env.module.unlock_research("fast_ships")
    assert result is False
    assert game_env.module.research_points == points_after_first


def test_automation_slot_research_increases_max_automated_ships(game_env):
    before = game_env.module.max_automated_ships()
    game_env.module.research_points = 100
    game_env.module.unlock_research("automation_slot")
    after = game_env.module.max_automated_ships()
    assert after == before + game_env.module.AUTOMATION_SLOT_RESEARCH_BONUS


def test_automation_slot_research_lets_a_third_ship_automate(game_env):
    game_env.module.total_profit = 10000
    game_env.module.automate_ship("1")
    game_env.module.automate_ship("2")
    assert game_env.module.automate_ship("3") is False  # capped at 2

    game_env.module.research_points = 100
    game_env.module.unlock_research("automation_slot")
    assert game_env.module.automate_ship("3") is True  # now 3 slots


def test_fast_ships_research_reduces_travel_ticks(game_env):
    assert game_env.module.travel_ticks() == game_env.module.TRAVEL_TICKS
    game_env.module.research_points = 100
    game_env.module.unlock_research("fast_ships")
    assert game_env.module.travel_ticks() == (
        game_env.module.TRAVEL_TICKS - game_env.module.FAST_SHIPS_TICK_REDUCTION
    )


def test_depart_uses_the_current_travel_ticks(game_env):
    game_env.module.research_points = 100
    game_env.module.unlock_research("fast_ships")
    game_env.load(ship_id="1")
    game_env.depart("verdant", ship_id="1")
    assert game_env.ship("1").transit_ticks_remaining == game_env.module.travel_ticks()


def test_hauler_research_increases_fleet_cargo_multiplier(game_env):
    assert game_env.module.fleet_cargo_multiplier() == 1.0
    game_env.module.research_points = 100
    game_env.module.unlock_research("hauler")
    assert game_env.module.fleet_cargo_multiplier() == game_env.module.HAULER_CARGO_MULTIPLIER


def test_hauler_research_increases_actual_cargo_loaded(game_env):
    game_env.load(ship_id="1")
    baseline_qty = game_env.ship("1").cargo_qty
    game_env.ship("1").cargo_qty = 0
    game_env.ship("1").cargo_good = None  # reset so load() isn't a no-op

    game_env.module.research_points = 100
    game_env.module.unlock_research("hauler")
    game_env.load(ship_id="1")
    assert game_env.ship("1").cargo_qty > baseline_qty


def test_render_shows_research_points(game_env):
    game_env.module.research_points = 42
    game_env.module.render()
    assert "42" in game_env.elements["research-points-display"].innerText


def test_render_shows_unlocked_node_status(game_env):
    game_env.module.research_points = 100
    game_env.module.unlock_research("fast_ships")
    game_env.module.render()
    text = game_env.elements["research-fast_ships-status"].innerText
    assert "unlocked" in text
    assert game_env.elements["research-fast_ships-unlock-button"].hidden is True


def test_unlock_button_disabled_without_enough_points(game_env):
    game_env.module.render()
    assert game_env.elements["research-fast_ships-unlock-button"].disabled is True


def test_unlock_button_click_dispatches(game_env):
    game_env.module.research_points = 100
    game_env.module.render()
    game_env.unlock_research("fast_ships")
    assert "fast_ships" in game_env.module.unlocked_research


def test_render_shows_updated_automation_slots_after_research(game_env):
    game_env.module.research_points = 100
    game_env.module.unlock_research("automation_slot")
    game_env.module.render()
    assert "0/3" in game_env.elements["automation-slots-display"].innerText
