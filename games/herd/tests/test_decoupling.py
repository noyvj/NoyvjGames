"""Milestone 3: decoupling measures — reduce the coupling ratio without
requiring herd shrinkage. Same herd size, lower emissions.
"""

import pytest


def test_no_decoupling_investment_leaves_base_ratio(game_env):
    assert game_env.farm.coupling_ratio() == 1.0


def test_feed_additive_reduces_coupling_ratio(game_env):
    game_env.invest_decoupling("feed")
    assert game_env.farm.coupling_ratio() == pytest.approx(0.96)


def test_herd_caps_reduces_coupling_ratio_by_its_own_amount(game_env):
    game_env.invest_decoupling("caps")
    assert game_env.farm.coupling_ratio() == pytest.approx(0.94)


def test_capture_systems_reduces_coupling_ratio_by_its_own_amount(game_env):
    game_env.invest_decoupling("capture")
    assert game_env.farm.coupling_ratio() == pytest.approx(0.90)


def test_measures_stack_together(game_env):
    game_env.invest_decoupling("feed")
    game_env.invest_decoupling("caps")
    game_env.invest_decoupling("capture")
    assert game_env.farm.coupling_ratio() == pytest.approx(1.0 - 0.04 - 0.06 - 0.10)


def test_repeated_investment_in_same_measure_stacks(game_env):
    for _ in range(3):
        game_env.invest_decoupling("feed")
    assert game_env.farm.coupling_ratio() == pytest.approx(1.0 - 3 * 0.04)


def test_coupling_ratio_floors_at_minimum(game_env):
    for _ in range(100):
        game_env.farm.funds = 1000
        game_env.invest_decoupling("capture")
    assert game_env.farm.coupling_ratio() == 0.1


def test_decoupling_investment_deducts_cost(game_env):
    game_env.invest_decoupling("feed")
    assert game_env.farm.funds == 300 - 15


def test_decoupling_investment_fails_when_unaffordable(game_env):
    game_env.farm.funds = 5
    game_env.invest_decoupling("capture")  # costs 30
    assert game_env.farm.decoupling_investment["capture"] == 0
    assert game_env.farm.funds == 5


def test_decoupling_does_not_shrink_herd(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.invest_decoupling("feed")
    assert game_env.farm.herd_size == 2


def test_same_herd_size_produces_less_methane_after_decoupling(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    undecoupled_methane = game_env.farm.methane_this_round()

    game_env.invest_decoupling("capture")
    decoupled_methane = game_env.farm.methane_this_round()

    assert decoupled_methane < undecoupled_methane
    assert game_env.farm.herd_size == 2  # same herd size both times


def test_render_shows_decoupling_counts_and_costs(game_env):
    game_env.invest_decoupling("feed")
    assert game_env.elements["feed-count"].innerText == "1"
    assert "15" in game_env.elements["feed-invest-button"].innerText
