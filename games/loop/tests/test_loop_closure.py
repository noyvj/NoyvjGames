"""Milestone 4: loop-closure visualization state — tracking and
surfacing what percentage of each cycle's production is circular vs.
new-extraction-sourced, plus a lifetime running share.
"""

import pytest


def test_circular_fraction_zero_by_default(game_env):
    assert game_env.chain.circular_fraction_this_cycle() == 0.0


def test_circular_fraction_reflects_investment(game_env):
    game_env.chain.invest_circularity("recycle")
    # 5 supply / 50 target
    assert game_env.chain.circular_fraction_this_cycle() == pytest.approx(0.1)


def test_circular_fraction_caps_at_one_when_closed(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    assert game_env.chain.circular_fraction_this_cycle() == pytest.approx(1.0)


def test_lifetime_circular_fraction_zero_before_any_cycle(game_env):
    assert game_env.chain.lifetime_circular_fraction() == 0.0


def test_lifetime_circular_fraction_zero_with_pure_extraction(game_env):
    game_env.chain.advance_cycle()
    game_env.chain.advance_cycle()
    assert game_env.chain.lifetime_circular_fraction() == 0.0


def test_lifetime_circular_fraction_reflects_mixed_history(game_env):
    game_env.chain.advance_cycle()  # 0% circular this cycle
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_circularity("recycle")
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.chain.advance_cycle()  # 100% circular this cycle
    # cycle 1: 50 extracted, cycle 2: 0 extracted, out of 100 total produced
    assert game_env.chain.total_produced == 100.0
    assert game_env.chain.total_extracted == 50.0
    assert game_env.chain.lifetime_circular_fraction() == pytest.approx(0.5)


def test_circular_fraction_log_records_each_cycle(game_env):
    game_env.chain.advance_cycle()
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.chain.advance_cycle()
    assert game_env.chain.circular_fraction_log == pytest.approx([0.0, 1.0])


def test_render_shows_circular_fraction_display(game_env):
    game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert "10%" in game_env.elements["circular-fraction-display"].innerText


def test_render_shows_lifetime_circular_display(game_env):
    game_env.module.render()
    assert "Lifetime circular share: 0%" == game_env.elements["lifetime-circular-display"].innerText


def test_render_updates_circular_bar_width(game_env):
    game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert game_env.elements["circular-bar"].style.width == "10%"
