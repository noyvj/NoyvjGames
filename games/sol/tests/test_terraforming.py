"""Tests for the Milestone 8 terraforming system: a per-planet progress bar
that accrues only under genuine sustained balance — ecology health above a
"thriving" bar (50%, stricter than the ecology system's own 10% crisis
line) AND real economic investment (at least one generator, Recycler, or
Trade Route). Below that bar, progress pauses; it never regresses, per the
project's "always recoverable, no dead-end states" rule."""

import math


# --- initial state -------------------------------------------------------

def test_terraform_starts_at_zero(game_env):
    assert game_env.earth["terraform_progress"] == 0.0
    assert game_env.elements["terraform-percent"].innerText == "0%"


def test_terraform_bar_starts_empty(game_env):
    assert game_env.elements["terraform-bar"].style.width == "0.0%"


def test_terraform_status_shows_paused_with_no_buildings(game_env):
    # Fresh game: 100% ecology, but zero investment — should still be paused.
    assert "Paused" in game_env.elements["terraform-status"].innerText
    assert "generator or Recycler" in game_env.elements["terraform-status"].innerText


def test_mars_terraform_independent_of_earth(game_env):
    assert game_env.mars["terraform_progress"] == 0.0


# --- has_economic_investment() -------------------------------------------

def test_no_investment_by_default(game_env):
    assert game_env.module.has_economic_investment("Earth") is False


def test_generator_counts_as_investment(game_env):
    game_env.earth["generator_count"] = 1
    assert game_env.module.has_economic_investment("Earth") is True


def test_recycler_counts_as_investment(game_env):
    game_env.earth["recycler_count"] = 1
    assert game_env.module.has_economic_investment("Earth") is True


def test_trade_route_counts_as_investment(game_env):
    game_env.earth["trade_route_count"] = 1
    assert game_env.module.has_economic_investment("Earth") is True


# --- terraform_rate() threshold behaviour --------------------------------

def test_rate_zero_with_no_investment_even_at_full_ecology(game_env):
    game_env.earth["ecology_health"] = 100.0
    assert game_env.module.terraform_rate("Earth") == 0.0


def test_rate_zero_below_ecology_threshold_even_with_investment(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 49.9
    assert game_env.module.terraform_rate("Earth") == 0.0


def test_rate_positive_exactly_at_threshold_with_investment(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 50.0
    assert game_env.module.terraform_rate("Earth") > 0.0


def test_rate_scales_with_ecology_health_above_threshold(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 50.0
    rate_at_50 = game_env.module.terraform_rate("Earth")
    game_env.earth["ecology_health"] = 100.0
    rate_at_100 = game_env.module.terraform_rate("Earth")
    assert math.isclose(rate_at_100, rate_at_50 * 2, abs_tol=1e-9)
    assert rate_at_100 > rate_at_50


def test_rate_at_full_ecology_matches_base_rate(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    assert math.isclose(
        game_env.module.terraform_rate("Earth"), game_env.module.TERRAFORM_BASE_RATE_PER_SEC, abs_tol=1e-9
    )


# --- accrual over ticks ---------------------------------------------------

def test_progress_accrues_when_balanced(game_env):
    # A Recycler alone (no generator) doesn't decay its own planet's
    # ecology, so 100% health holds steady for a clean full-rate check.
    game_env.earth["recycler_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.timers.tick_intervals(10)  # 1 second at full rate
    assert math.isclose(
        game_env.earth["terraform_progress"], game_env.module.TERRAFORM_BASE_RATE_PER_SEC, abs_tol=1e-6
    )


def test_progress_does_not_accrue_without_investment(game_env):
    game_env.earth["ecology_health"] = 100.0  # no buildings at all
    game_env.timers.tick_intervals(50)
    assert game_env.earth["terraform_progress"] == 0.0


def test_progress_does_not_accrue_below_ecology_threshold(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 40.0
    game_env.timers.tick_intervals(50)
    assert game_env.earth["terraform_progress"] == 0.0


def test_progress_clamps_at_100(game_env):
    game_env.earth["recycler_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.timers.tick_intervals(20000)  # far more than enough to max out
    assert game_env.earth["terraform_progress"] == 100.0


def test_lone_generator_with_no_recycler_eventually_stalls_terraforming(game_env):
    # Emergent property, not a bug: a generator decays its own planet's
    # ecology (1%/s) with nothing to counteract it, so health eventually
    # drops below the 50% terraform bar and progress pauses on its own —
    # sustaining terraforming genuinely requires a Recycler (or Trade
    # Route aid), not just any building.
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.timers.tick_intervals(1000)  # 100 seconds: ecology -> ~0%
    assert math.isclose(game_env.earth["ecology_health"], 0.0, abs_tol=1e-6)
    stalled_progress = game_env.earth["terraform_progress"]

    game_env.timers.tick_intervals(50)
    assert game_env.earth["terraform_progress"] == stalled_progress


def test_earth_and_mars_terraform_independently(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.mars["ecology_health"] = 100.0  # no investment on Mars
    game_env.timers.tick_intervals(10)
    assert game_env.earth["terraform_progress"] > 0.0
    assert game_env.mars["terraform_progress"] == 0.0


# --- pause, never regress --------------------------------------------------

def test_progress_pauses_but_does_not_regress_when_ecology_drops(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.timers.tick_intervals(10)
    progress_before = game_env.earth["terraform_progress"]
    assert progress_before > 0.0

    game_env.earth["ecology_health"] = 20.0  # below the 50% terraform bar
    game_env.timers.tick_intervals(50)
    assert game_env.earth["terraform_progress"] == progress_before


def test_progress_resumes_once_balance_is_restored(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 20.0
    game_env.timers.tick_intervals(20)
    assert game_env.earth["terraform_progress"] == 0.0

    game_env.earth["ecology_health"] = 80.0
    game_env.timers.tick_intervals(10)
    assert game_env.earth["terraform_progress"] > 0.0


# --- display formatting ----------------------------------------------------

def test_display_rounds_percent(game_env):
    game_env.earth["terraform_progress"] = 42.6
    game_env.module.update_terraform_display("Earth")
    assert game_env.elements["terraform-percent"].innerText == "43%"


def test_display_bar_width_tracks_raw_progress(game_env):
    game_env.earth["terraform_progress"] = 37.5
    game_env.module.update_terraform_display("Earth")
    assert game_env.elements["terraform-bar"].style.width == "37.5%"


def test_status_clears_once_actually_accruing(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 100.0
    game_env.module.update_terraform_display("Earth")
    assert game_env.elements["terraform-status"].innerText == ""


def test_status_explains_missing_investment(game_env):
    game_env.earth["ecology_health"] = 100.0
    game_env.module.update_terraform_display("Earth")
    assert "generator or Recycler" in game_env.elements["terraform-status"].innerText


def test_status_explains_ecology_below_threshold(game_env):
    game_env.earth["generator_count"] = 1
    game_env.earth["ecology_health"] = 38.0
    game_env.module.update_terraform_display("Earth")
    status = game_env.elements["terraform-status"].innerText
    assert "38%" in status
    assert "50%" in status


def test_buying_first_generator_immediately_updates_terraform_status(game_env):
    # Regression-style: the status should reflect new investment right
    # away, not wait up to 100ms for the next tick.
    game_env.earth["ecology_health"] = 100.0
    assert "generator or Recycler" in game_env.elements["terraform-status"].innerText

    game_env.earth["resource_count"] = 10
    game_env.buy_generator()
    assert game_env.elements["terraform-status"].innerText == ""


# --- Mars-specific wiring --------------------------------------------------

def test_mars_terraform_display_updates(game_env):
    game_env.mars["recycler_count"] = 1
    game_env.mars["ecology_health"] = 100.0
    game_env.timers.tick_intervals(60)  # 6 seconds -> 0.6%, rounds to 1%
    assert game_env.elements["mars-terraform-percent"].innerText != "0%"


def test_mars_terraform_status_independent_message(game_env):
    game_env.mars["ecology_health"] = 100.0
    game_env.module.update_terraform_display("Mars")
    assert "generator or Recycler" in game_env.elements["mars-terraform-status"].innerText
