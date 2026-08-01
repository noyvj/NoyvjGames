# Plain string constants mirroring game.py's state values. Not imported
# from `game` directly — game.py imports `js`/`pyodide.ffi`, which only
# exist once the game_env fixture installs the fake-DOM shims, so the
# module can't be imported at collection time.
PRESERVED = "preserved"
BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"


def test_grid_has_expected_size(game_env):
    assert len(game_env.module.plots) == 36


def test_plots_start_preserved(game_env):
    assert all(plot.state == PRESERVED for plot in game_env.module.plots)


def test_clear_preserved_plot_becomes_bare(game_env):
    game_env.select(0)
    game_env.clear()
    assert game_env.plot(0).state == BARE


def test_clear_recovered_plot_becomes_bare(game_env):
    plot = game_env.plot(0)
    plot.state = RECOVERED
    game_env.select(0)
    game_env.clear()
    assert plot.state == BARE


def test_clear_is_a_noop_on_bare_plot(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.select(0)
    game_env.clear()
    assert plot.state == BARE


def test_clear_is_a_noop_on_replanting_plot(game_env):
    plot = game_env.plot(0)
    plot.state = REPLANTING
    game_env.select(0)
    game_env.clear()
    assert plot.state == REPLANTING


def test_replant_bare_plot_starts_replanting(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.select(0)
    game_env.replant()
    assert plot.state == REPLANTING


def test_replant_is_a_noop_on_preserved_plot(game_env):
    game_env.select(0)
    game_env.replant()
    assert game_env.plot(0).state == PRESERVED


def test_replant_is_a_noop_on_recovered_plot(game_env):
    plot = game_env.plot(0)
    plot.state = RECOVERED
    game_env.select(0)
    game_env.replant()
    assert plot.state == RECOVERED


def test_finish_recovery_transitions_replanting_to_recovered(game_env):
    plot = game_env.plot(0)
    plot.state = REPLANTING
    assert plot.finish_recovery() is True
    assert plot.state == RECOVERED


def test_finish_recovery_is_a_noop_outside_replanting(game_env):
    plot = game_env.plot(0)
    plot.state = PRESERVED
    assert plot.finish_recovery() is False
    assert plot.state == PRESERVED


def test_action_buttons_get_real_labels_on_setup(game_env):
    assert game_env.elements["clear-button"].innerText == "Clear"
    assert game_env.elements["replant-button"].innerText == "Replant"


def test_action_buttons_disabled_with_no_selection(game_env):
    assert game_env.elements["clear-button"].disabled is True
    assert game_env.elements["replant-button"].disabled is True


def test_selecting_preserved_plot_enables_clear_only(game_env):
    game_env.select(0)
    assert game_env.elements["clear-button"].disabled is False
    assert game_env.elements["replant-button"].disabled is True


def test_selecting_bare_plot_enables_replant_only(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.select(0)
    assert game_env.elements["clear-button"].disabled is True
    assert game_env.elements["replant-button"].disabled is False


def test_selecting_replanting_plot_disables_both_actions(game_env):
    plot = game_env.plot(0)
    plot.state = REPLANTING
    game_env.select(0)
    assert game_env.elements["clear-button"].disabled is True
    assert game_env.elements["replant-button"].disabled is True


def test_click_on_rendered_tile_selects_plot(game_env):
    game_env.select_tile_click(3)
    assert "Plot 3: Preserved" in game_env.elements["selected-plot-state"].innerText


def test_clear_with_no_selection_does_nothing(game_env):
    # No plot selected yet — clicking Clear should be a safe no-op.
    game_env.clear()
    assert all(plot.state == PRESERVED for plot in game_env.module.plots)


def test_grid_tiles_reflect_state_via_class_name(game_env):
    plot = game_env.plot(5)
    plot.state = BARE
    game_env.module.render()
    tile = game_env.elements["plot-5"]
    assert "plot-bare" in tile.className
