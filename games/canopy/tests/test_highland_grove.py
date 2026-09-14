"""B3 (planning/TODO.md "Per-game: Canopy"): a second, unlockable forest
region. Highland Grove reuses the Plot class and its clear/replant/
accrue_tick() mechanics directly on a smaller (3x4), independent grid --
no biodiversity or stakeholder tension of its own. Unlocks permanently
(a sticky, one-way flag) once the main forest's standing value crosses
HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD."""


def _unlock_highland(game_env):
    """Directly flips the unlock flag and lets one tick pass so
    accrual/rendering paths that gate on `highland_unlocked` actually
    run -- faster than ticking enough times to grow 36 plots to 2000
    standing value for every test that just needs the grove open."""
    m = game_env.module
    m.highland_unlocked = True
    game_env.tick(1)


def test_highland_starts_locked(game_env):
    m = game_env.module
    assert m.highland_unlocked is False
    assert game_env.elements["highland-section"].hidden is True
    assert game_env.elements["highland-lock-banner"].hidden is False


def test_lock_banner_shows_progress(game_env):
    m = game_env.module
    game_env.tick(5)
    m.render()
    banner_text = game_env.elements["highland-lock-banner"].innerText
    assert "locked" in banner_text.lower()
    assert f"{m.HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f}" in banner_text


def test_unlocking_reveals_the_section(game_env):
    _unlock_highland(game_env)
    assert game_env.elements["highland-section"].hidden is False
    assert game_env.elements["highland-lock-banner"].hidden is True


def test_unlock_is_automatic_once_threshold_crossed(game_env):
    m = game_env.module
    # Force every plot's value high enough to cross the threshold without
    # waiting out real accrual ticks.
    for plot in m.plots:
        plot.value = m.HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD
    assert m.highland_unlocked is False
    game_env.tick(1)
    assert m.highland_unlocked is True


def test_unlock_is_sticky_even_if_standing_value_drops_after(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = m.HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD
    game_env.tick(1)
    assert m.highland_unlocked is True
    for plot in m.plots:
        plot.value = 0.0
    game_env.tick(1)
    assert m.highland_unlocked is True  # never re-locks


def test_highland_plots_do_not_accrue_before_unlock(game_env):
    m = game_env.module
    game_env.tick(10)
    assert m.highland_standing_value() == 0.0
    assert all(plot.ticks_intact == 0 for plot in m.highland_plots)


def test_highland_plots_accrue_once_unlocked(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    game_env.tick(5)
    assert m.highland_standing_value() > 0


def test_highland_grid_has_its_own_size(game_env):
    m = game_env.module
    assert len(m.highland_plots) == m.HIGHLAND_ROWS * m.HIGHLAND_COLS
    assert len(m.highland_plots) == 12


def test_highland_coordinate_label_uses_highland_cols(game_env):
    m = game_env.module
    assert m.highland_plot_coordinate_label(0) == "A1"
    assert m.highland_plot_coordinate_label(m.HIGHLAND_COLS - 1) == "D1"
    assert m.highland_plot_coordinate_label(m.HIGHLAND_COLS) == "A2"


def test_select_and_clear_a_highland_plot(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    game_env.tick(5)
    game_env.highland_select(0)
    value_before = m.highland_plots[0].value
    assert value_before > 0

    game_env.highland_clear()

    assert m.highland_plots[0].state == m.BARE
    assert m.highland_income == value_before


def test_select_and_replant_a_bare_highland_plot(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    game_env.highland_select(0)
    game_env.highland_clear()
    assert m.highland_plots[0].state == m.BARE

    game_env.highland_replant()

    assert m.highland_plots[0].state == m.REPLANTING


def test_highland_click_wires_up_selection_via_dom(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    m.render()  # rebuild highland tiles so highland-plot-0 exists
    game_env.highland_select_tile_click(0)
    assert m.highland_selected_index == 0


def test_highland_tile_grid_columns_match_highland_cols(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    m.render()
    grid = game_env.elements["highland-plot-grid"]
    assert grid.getAttribute("data-cols") == str(m.HIGHLAND_COLS)
    assert grid.style.gridTemplateColumns == f"repeat({m.HIGHLAND_COLS}, 1fr)"


def test_reset_session_relocks_highland(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    game_env.tick(3)
    game_env.highland_select(0)
    game_env.highland_clear()
    assert m.highland_unlocked is True

    game_env.reset_session()

    assert m.highland_unlocked is False
    assert m.highland_income == 0.0
    assert m.highland_selected_index is None
    assert len(m.highland_plots) == 12
    assert all(plot.value == 0.0 for plot in m.highland_plots)


def test_second_growth_achievement_earns_on_unlock(game_env):
    m = game_env.module
    assert "second_growth" not in m.achievement_ids_earned()
    _unlock_highland(game_env)
    assert "second_growth" in m.achievement_ids_earned()


def test_save_and_load_round_trips_highland_state(game_env):
    m = game_env.module
    _unlock_highland(game_env)
    game_env.tick(5)
    game_env.highland_select(2)
    game_env.highland_clear()
    data = m.get_state()
    assert data["highland_unlocked"] is True
    assert data["highland_income"] > 0

    game_env.reset_session()
    assert m.highland_unlocked is False

    m.load_state(data)
    assert m.highland_unlocked is True
    assert m.highland_income == data["highland_income"]
    assert m.highland_plots[2].state == m.BARE


def test_load_state_without_highland_keys_keeps_current_live_value(game_env):
    """A save predating B3 simply lacks these keys. Matching every other
    backward-compat field's documented convention in load_state() (see
    its own comment above the block this test targets), a missing key
    falls back to whatever's currently live rather than crashing on a
    missing key or being force-reset -- it must NOT crash either way."""
    m = game_env.module
    data = m.get_state()
    for key in ("highland_unlocked", "highland_selected_index", "highland_income", "highland_plots"):
        del data[key]

    # Starting from the fresh-module default (never unlocked): the
    # missing keys leave it exactly as it already was.
    m.load_state(data)
    assert m.highland_unlocked is False
    assert m.highland_income == 0.0
    assert len(m.highland_plots) == 12
