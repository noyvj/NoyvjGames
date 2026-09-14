"""B2 (planning/TODO.md "Per-game: Canopy"): a "reset session" option, and
B13: a larger-grid difficulty/length variant -- folded into one
`reset_session()` entry point in game.py since both mean "rebuild the whole
session from scratch," just optionally at a different GRID_SIZE_PRESETS
size."""


def test_reset_session_restores_fresh_defaults(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()
    assert m.total_income > 0

    game_env.reset_session()

    assert m.total_income == 0.0
    assert m.community_relations == m.STARTING_COMMUNITY_RELATIONS
    assert m.selected_index is None
    assert m.pending_stakeholder_request is None
    assert all(plot.value == 0.0 and plot.state == m.PRESERVED for plot in m.plots)
    assert len(m.plots) == 36  # still "normal" (6x6) -- reset alone doesn't change size


def test_reset_session_does_not_touch_personal_best(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()
    best_income_before = m.personal_best["income"]
    assert best_income_before > 0

    game_env.reset_session()

    assert m.personal_best["income"] == best_income_before


def test_grid_size_select_defaults_to_normal(game_env):
    assert game_env.elements["grid-size-select"].value == "normal"


def test_changing_grid_size_to_large_rebuilds_plots(game_env):
    m = game_env.module
    game_env.change_grid_size("large")
    assert m.current_grid_size == "large"
    assert m.GRID_ROWS, m.GRID_COLS == (9, 8)
    assert len(m.plots) == 9 * 8


def test_changing_grid_size_resets_progress(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.select(0)
    game_env.clear()
    assert m.total_income > 0

    game_env.change_grid_size("large")

    assert m.total_income == 0.0
    assert len(m.plots) == 72


def test_changing_grid_size_back_to_normal_shrinks_plots_again(game_env):
    m = game_env.module
    game_env.change_grid_size("large")
    assert len(m.plots) == 72
    game_env.change_grid_size("normal")
    assert len(m.plots) == 36


def test_reset_session_after_large_keeps_large_size(game_env):
    """A plain Reset Session (not a grid-size change) should preserve
    whatever size is currently selected rather than silently reverting to
    "normal"."""
    m = game_env.module
    game_env.change_grid_size("large")
    game_env.reset_session()
    assert m.current_grid_size == "large"
    assert len(m.plots) == 72


def test_reset_session_destroys_old_click_proxies(game_env):
    m = game_env.module
    game_env.tick(1)  # force at least one render so proxies exist
    old_proxies = list(m._plot_click_proxies.values())
    assert old_proxies
    game_env.reset_session()
    assert all(p.destroyed for p in old_proxies)


def test_save_and_load_round_trips_grid_size(game_env):
    m = game_env.module
    game_env.change_grid_size("large")
    game_env.tick(3)
    game_env.select(5)
    game_env.clear()
    data = m.get_state()
    assert data["current_grid_size"] == "large"

    # Simulate loading this save into a fresh "normal"-sized module.
    game_env.change_grid_size("normal")
    assert len(m.plots) == 36

    m.load_state(data)
    assert m.current_grid_size == "large"
    assert len(m.plots) == 72
    assert m.plots[5].state == m.BARE  # the cleared plot's state round-tripped


def test_load_state_without_grid_size_field_defaults_to_normal(game_env):
    """A save predating B13 simply lacks the key -- must not crash, and
    must be treated as "normal" (the only size that existed then)."""
    m = game_env.module
    data = m.get_state()
    del data["current_grid_size"]
    game_env.change_grid_size("large")  # move away from normal first
    m.load_state(data)
    assert m.current_grid_size == "normal"
    assert len(m.plots) == 36


def test_invalid_grid_size_is_ignored(game_env):
    m = game_env.module
    result = m.reset_session(grid_size="huge")
    assert result is False
    assert m.current_grid_size == "normal"
    assert len(m.plots) == 36
