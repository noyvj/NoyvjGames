"""Iteration pass: a delayed-effect ticker log, a distinct sea-level
meter, and a before/now coastline comparison.
"""

import pytest


def test_sea_level_fraction_starts_at_zero(game_env):
    assert game_env.state.sea_level_fraction() == 0.0


def test_sea_level_fraction_rises_with_sea_level(game_env):
    game_env.advance_season()
    assert game_env.state.sea_level_fraction() == pytest.approx(
        5.0 / game_env.module.SEA_LEVEL_METER_MAX
    )


def test_sea_level_fraction_caps_at_one(game_env):
    game_env.state.sea_level = 10_000.0
    assert game_env.state.sea_level_fraction() == 1.0


def test_ticker_log_empty_before_any_season(game_env):
    assert game_env.state.ticker_log == []


def test_ticker_log_records_rising_acidity_before_lag_arrives(game_env):
    game_env.invest("output")
    game_env.advance_season()
    assert len(game_env.state.ticker_log) == 1
    assert "won't show" in game_env.state.ticker_log[0]


def test_ticker_log_records_fish_decline_once_lag_arrives(game_env):
    game_env.invest("output")
    for _ in range(game_env.module.FISH_LAG_SEASONS + 1):
        game_env.advance_season()
    assert any("quietly declining" in msg for msg in game_env.state.ticker_log)


def test_ticker_log_caps_at_limit(game_env):
    game_env.invest("output")
    for _ in range(10):
        game_env.advance_season()
    assert len(game_env.state.ticker_log) <= game_env.module.TICKER_LOG_LIMIT


def test_ticker_log_silent_with_no_investment(game_env):
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.ticker_log == []


def test_render_shows_ticker_placeholder_by_default(game_env):
    game_env.module.render()
    assert game_env.elements["ticker-log"].innerHTML == "No notable changes yet."


def test_render_shows_ticker_messages_after_investment(game_env):
    game_env.invest("output")
    game_env.advance_season()
    game_env.module.render()
    assert "won't show" in game_env.elements["ticker-log"].innerHTML


def test_render_updates_sea_level_bar_width(game_env):
    game_env.advance_season()
    game_env.module.render()
    expected = f"{game_env.state.sea_level_fraction() * 100:.0f}%"
    assert game_env.elements["sea-level-bar"].style.width == expected


def test_render_coastline_before_grid_is_always_all_land(game_env):
    for _ in range(5):
        game_env.advance_season()
    game_env.module.render()
    # before-grid always reflects season 1 (sea_level 0) -> no flooded tiles
    before_children = game_env.elements["coastline-before-grid"].children
    assert all("coastline-flooded" not in tile.className for tile in before_children)


def test_render_coastline_now_grid_reflects_current_sea_level(game_env):
    for _ in range(10):
        game_env.advance_season()
    game_env.module.render()
    now_children = game_env.elements["coastline-now-grid"].children
    assert any("coastline-flooded" in tile.className for tile in now_children)


def test_render_coastline_now_label_shows_current_season(game_env):
    game_env.advance_season()
    game_env.advance_season()
    game_env.module.render()
    assert game_env.elements["coastline-now-label"].innerText == "Season 3"
