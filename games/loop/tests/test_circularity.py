"""Milestone 2: circularity investments — repair/reuse/recycling
infrastructure that supplies part of the production target without new
extraction. Enough investment can close the loop entirely (extraction
hits zero).
"""

import pytest


def test_investments_start_at_zero(game_env):
    for measure in ("repair", "reuse", "recycle"):
        assert game_env.chain.circularity_investment[measure] == 0


def test_repair_investment_adds_circular_supply(game_env):
    game_env.chain.invest_circularity("repair")
    assert game_env.chain.circular_supply() == pytest.approx(3.0)


def test_reuse_investment_adds_circular_supply(game_env):
    game_env.chain.invest_circularity("reuse")
    assert game_env.chain.circular_supply() == pytest.approx(4.0)


def test_recycle_investment_adds_circular_supply(game_env):
    game_env.chain.invest_circularity("recycle")
    assert game_env.chain.circular_supply() == pytest.approx(5.0)


def test_investments_stack_across_measures(game_env):
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_circularity("reuse")
    game_env.chain.invest_circularity("recycle")
    assert game_env.chain.circular_supply() == pytest.approx(12.0)


def test_investment_spends_funds(game_env):
    funds_before = game_env.chain.funds
    game_env.chain.invest_circularity("recycle")
    assert game_env.chain.funds == pytest.approx(funds_before - 30)


def test_investment_fails_when_insufficient_funds(game_env):
    game_env.chain.funds = 5.0
    result = game_env.chain.invest_circularity("recycle")
    assert result is False
    assert game_env.chain.circularity_investment["recycle"] == 0


def test_circular_supply_reduces_new_extraction_needed(game_env):
    game_env.chain.invest_circularity("recycle")
    # 50 target - 5 circular supply = 45 new extraction
    assert game_env.chain.new_extraction_needed() == pytest.approx(45.0)


def test_loop_not_closed_by_default(game_env):
    assert game_env.chain.is_loop_closed() is False


def test_enough_investment_closes_the_loop(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    # 10 * 5 supply == 50 production target
    assert game_env.chain.circular_supply() == pytest.approx(50.0)
    assert game_env.chain.new_extraction_needed() == 0.0
    assert game_env.chain.is_loop_closed() is True


def test_extraction_needed_never_goes_negative(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(20):
        game_env.chain.invest_circularity("recycle")
    assert game_env.chain.new_extraction_needed() == 0.0


def test_advance_cycle_uses_reduced_extraction_for_cost(game_env):
    game_env.chain.invest_circularity("recycle")
    funds_before = game_env.chain.funds
    game_env.chain.advance_cycle()
    # 45 extraction * 2 cost = 90; revenue 50*5 = 250; net = 160
    assert game_env.chain.funds == pytest.approx(funds_before + 160.0)


def test_render_shows_investment_counts(game_env):
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_circularity("repair")
    game_env.module.render()
    assert game_env.elements["repair-count"].innerText == "2"


def test_render_shows_loop_closed_message(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert "closed" in game_env.elements["extraction-display"].innerText.lower()
