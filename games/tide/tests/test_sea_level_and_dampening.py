"""Milestone 3: sea-level rise is unconditional — adaptation investment
never slows or stops it, only dampens how much economic damage it causes.
"""

import pytest


def test_sea_level_starts_at_zero(game_env):
    assert game_env.state.sea_level == 0.0


def test_sea_level_rises_every_season(game_env):
    game_env.advance_season()
    assert game_env.state.sea_level == 5.0


def test_sea_level_rise_is_identical_with_or_without_adaptation(game_env):
    for _ in range(5):
        game_env.invest("adaptation")
    game_env.advance_season()
    assert game_env.state.sea_level == 5.0  # exactly SEA_LEVEL_RISE_PER_SEASON, no discount


def test_sea_level_accumulates_across_seasons(game_env):
    game_env.advance_season()
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.sea_level == 15.0


def test_dampening_fraction_is_zero_with_no_adaptation(game_env):
    assert game_env.state.dampening_fraction() == 0.0


def test_dampening_fraction_increases_with_adaptation(game_env):
    for _ in range(3):  # crosses the first tier threshold (Sandbag berms)
        game_env.invest("adaptation")
    assert game_env.state.dampening_fraction() == pytest.approx(0.3)


def test_dampening_fraction_caps_at_maximum(game_env):
    game_env.state.capacity["adaptation"] = 1000
    assert game_env.state.dampening_fraction() == 0.9


def test_cumulative_damage_matches_full_rise_without_adaptation(game_env):
    game_env.advance_season()
    assert game_env.state.cumulative_damage == 5.0


def test_cumulative_damage_is_reduced_by_adaptation(game_env):
    for _ in range(3):  # dampening = 0.3 (Sandbag berms tier)
        game_env.invest("adaptation")
    game_env.advance_season()
    assert game_env.state.cumulative_damage == pytest.approx(5.0 * (1 - 0.3))


def test_cumulative_damage_grows_slower_with_more_adaptation(game_env):
    for _ in range(5):
        game_env.invest("adaptation")
    game_env.advance_season()
    low_damage = game_env.state.cumulative_damage

    game_env.state.capacity["adaptation"] = 0
    game_env.state.cumulative_damage = 0.0
    game_env.advance_season()
    high_damage = game_env.state.cumulative_damage

    assert low_damage < high_damage


def test_adaptation_never_fully_eliminates_damage(game_env):
    # Even maxed-out dampening still lets some damage through — adaptation
    # buys time, it doesn't stop the sea.
    game_env.state.capacity["adaptation"] = 1000
    game_env.advance_season()
    assert game_env.state.cumulative_damage > 0.0


def test_render_shows_sea_level_and_damage(game_env):
    game_env.advance_season()
    assert "5" in game_env.elements["sea-level-display"].innerText
    assert "5" in game_env.elements["damage-display"].innerText
