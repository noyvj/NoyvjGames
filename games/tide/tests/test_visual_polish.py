"""Milestone 7: visual pass — acidity/fish-yield meter bars alongside
their numbers.
"""


def test_acidity_bar_starts_empty(game_env):
    assert game_env.elements["acidity-bar"].style.width == "0%"


def test_acidity_bar_fills_as_acidity_rises(game_env):
    game_env.invest("output")
    game_env.advance_season()
    game_env.module.render()
    assert game_env.elements["acidity-bar"].style.width != "0%"


def test_acidity_bar_caps_at_full(game_env):
    game_env.state.acidity = 999999.0
    game_env.module.render()
    assert game_env.elements["acidity-bar"].style.width == "100%"


def test_fish_yield_bar_starts_full(game_env):
    assert game_env.elements["fish-yield-bar"].style.width == "100%"


def test_fish_yield_bar_shrinks_as_yield_degrades(game_env):
    game_env.state.acidity_history = [999999.0, 999999.0, 999999.0]
    game_env.module.render()
    assert game_env.elements["fish-yield-bar"].style.width == "20%"  # MIN_FISH_MULTIPLIER
