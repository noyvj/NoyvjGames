"""V-CD-5 (planning/TODO.md section N, completion-audit fix): the original
B3 idea specified Highland Grove should have genuinely different
degradation/compounding rates than the main forest, not just a same-rules
bonus copy. Highland Grove is framed as a high-altitude ecosystem (its
lock banner/blurb, mountain iconography), so the distinction is grounded
in real alpine-ecology tradeoffs: thin alpine soil erodes faster once
disturbed (HIGHLAND_DEGRADE_MULTIPLIER), while a harsher, shorter growing
season means standing value compounds more slowly (HIGHLAND_GROWTH_
MULTIPLIER). Both apply only to Highland plots -- the main forest is
untouched."""

import pytest


def _unlock_highland(game_env):
    m = game_env.module
    m.highland_unlocked = True
    game_env.tick(1)


def test_highland_multipliers_are_distinct_from_parity(game_env):
    m = game_env.module
    assert m.HIGHLAND_DEGRADE_MULTIPLIER != 1.0
    assert m.HIGHLAND_GROWTH_MULTIPLIER != 1.0


def test_main_forest_degradation_is_byte_for_byte_unchanged(game_env):
    """A regression guard: Highland's own multiplier must never leak onto
    a main-forest Plot, which always defaults to region="main"."""
    m = game_env.module
    plot = m.plots[0]
    assert plot.region == "main"
    plot.clear_count = 3
    expected = max(
        m.MIN_PRODUCTIVITY_MULTIPLIER,
        1 - m.current_degrade_per_clear() * plot.clear_count,
    )
    assert plot.productivity_multiplier() == expected


def test_highland_soil_degrades_faster_than_main_forest(game_env):
    m = game_env.module
    main_plot = m.plots[0]
    highland_plot = m.highland_plots[0]
    assert highland_plot.region == "highland"
    main_plot.clear_count = 2
    highland_plot.clear_count = 2

    main_productivity = main_plot.productivity_multiplier()
    highland_productivity = highland_plot.productivity_multiplier()

    # Lower productivity_multiplier == more degraded, so Highland (faster
    # degrading) must read lower than the main forest at the same
    # clear_count.
    assert highland_productivity < main_productivity


def test_highland_value_compounds_slower_than_main_forest(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    main_plot = m.plots[0]
    highland_plot = m.highland_plots[0]

    # Both plots start fresh (PRESERVED, ticks_intact=0, no season/legacy
    # drift within the same single tick), so any difference in the value
    # actually accrued this tick is purely the growth multiplier's doing.
    main_plot.accrue_tick()
    highland_plot.accrue_tick()

    assert highland_plot.value < main_plot.value


def test_highland_multiplier_is_a_flat_ratio_of_the_main_forest_growth(game_env):
    """Pins the exact HIGHLAND_GROWTH_MULTIPLIER relationship, not just
    "slower than" -- catches a future change to the constant's value
    silently drifting the actual ratio."""
    m = game_env.module
    _unlock_highland(game_env)
    main_plot = m.plots[0]
    highland_plot = m.highland_plots[0]

    main_delta = main_plot.accrue_tick()
    highland_delta = highland_plot.accrue_tick()

    assert highland_delta == pytest.approx(main_delta * m.HIGHLAND_GROWTH_MULTIPLIER, rel=1e-9)


def test_reset_session_rebuilds_highland_plots_with_highland_region(game_env):
    """Guards the two construction sites (module load + reset_session())
    that both need region="highland" -- a missed one would silently
    revert Highland Grove to main-forest rates after any reset."""
    m = game_env.module
    game_env.reset_session()
    assert all(plot.region == "highland" for plot in m.highland_plots)
