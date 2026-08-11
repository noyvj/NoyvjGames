"""Iteration pass: animated flow along the chain-flow diagram (return-
flow visibility tied to circular fraction), goods-category flavor
naming, and an illustrative real-world circularity comparison.
"""

import pytest


def test_extraction_display_includes_goods_label(game_env):
    game_env.module.render()
    assert game_env.module.GOODS_LABEL in game_env.elements["extraction-display"].innerText


def test_production_display_includes_goods_label(game_env):
    game_env.module.render()
    assert game_env.module.GOODS_LABEL in game_env.elements["production-display"].innerText


def test_return_flow_opacity_zero_by_default(game_env):
    game_env.module.render()
    assert game_env.elements["return-flow-row"].style.opacity == "0.00"


def test_return_flow_opacity_matches_circular_fraction(game_env):
    game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert game_env.elements["return-flow-row"].style.opacity == "0.10"


def test_return_flow_opacity_full_when_loop_closed(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.module.render()
    assert game_env.elements["return-flow-row"].style.opacity == "1.00"


def test_real_world_comparison_below_benchmark_message(game_env):
    msg = game_env.module.real_world_comparison_message(0.0)
    assert "0%" in msg
    assert "7%" in msg


def test_real_world_comparison_above_benchmark_message(game_env):
    msg = game_env.module.real_world_comparison_message(0.5)
    assert "above" in msg
    assert "50%" in msg


def test_render_shows_real_world_comparison(game_env):
    game_env.module.render()
    text = game_env.elements["real-world-comparison-display"].innerText
    assert "circular" in text
    assert "7%" in text
