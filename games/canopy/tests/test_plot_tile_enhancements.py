"""B8 (hover/tap tooltips), B9 (colorblind-safe pattern/icon overlay),
B16 (keyboard navigation -- the data-cols hook game.py provides for it),
B17 (floating "+X value" pop), and B19 (fully-mature cap-off visual for
Recovered), from planning/TODO.md's "Per-game: Canopy" section."""


def test_grid_carries_column_count_for_keyboard_nav(game_env):
    m = game_env.module
    assert game_env.elements["plot-grid"].getAttribute("data-cols") == str(m.GRID_COLS)


def test_tile_tooltip_includes_coordinate_state_value_and_soil(game_env):
    m = game_env.module
    m.plots[0].value = 12.34
    m.plots[0].clear_count = 1  # 90% productivity after one clear
    game_env.select(0)  # re-render so the tile picks up the new value
    text = game_env.elements["plot-0"].getAttribute("data-tooltip")
    assert "A1" in text
    assert "Preserved" in text
    assert "12.3" in text
    assert "90%" in text


def test_tile_tooltip_shows_recovery_countdown_when_replanting(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    game_env.select(0)
    game_env.replant()
    text = game_env.elements["plot-0"].getAttribute("data-tooltip")
    assert f"recovering in {m.RECOVERY_TICKS} ticks" in text


def test_tile_has_aria_label_matching_tooltip(game_env):
    tile = game_env.elements["plot-0"]
    assert tile.getAttribute("aria-label") == tile.getAttribute("data-tooltip")


def test_bare_plot_has_a_pattern_class_hook(game_env):
    # The actual pattern is pure CSS (style.css's .plot-tile.plot-bare
    # ::before etc.) -- this just confirms every state keeps its own
    # distinct class so those selectors have something to key off.
    game_env.select(0)
    game_env.clear()
    assert "plot-bare" in game_env.elements["plot-0"].className


def test_fully_mature_class_appears_only_for_capped_recovered_plots(game_env):
    m = game_env.module
    m.plots[0].state = m.RECOVERED
    m.plots[0].ticks_intact = m.MATURITY_TICKS - 1
    game_env.select(0)
    assert "plot-fully-mature" not in game_env.elements["plot-0"].className

    m.plots[0].ticks_intact = m.MATURITY_TICKS
    game_env.select(0)
    assert "plot-fully-mature" in game_env.elements["plot-0"].className


def test_fully_mature_class_does_not_appear_for_preserved_plots(game_env):
    """B19 is specifically about Recovered's cap-off -- a fully-matured
    never-cleared Preserved plot doesn't need the same "restoration
    finished" visual, since it was never degraded to begin with."""
    m = game_env.module
    m.plots[0].state = m.PRESERVED
    m.plots[0].ticks_intact = m.MATURITY_TICKS
    game_env.select(0)
    assert "plot-fully-mature" not in game_env.elements["plot-0"].className


def test_value_pop_appears_after_a_tick_with_meaningful_growth(game_env):
    game_env.tick(1)
    tile = game_env.elements["plot-0"]
    pops = [c for c in tile.children if c.className.startswith("value-pop")]
    assert len(pops) == 1
    assert pops[0].innerText.startswith("+")


def test_value_pop_is_cleared_on_the_next_render_without_a_new_tick(game_env):
    game_env.tick(1)
    game_env.select(0)  # a plain render, no new tick
    tile = game_env.elements["plot-0"]
    pops = [c for c in tile.children if c.className == "value-pop"]
    assert pops == []


def test_no_value_pop_for_bare_or_replanting_plots(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.tick(1)
    tile = game_env.elements["plot-0"]
    pops = [c for c in tile.children if c.className == "value-pop"]
    assert pops == []


def test_accrue_tick_returns_the_delta_it_added(game_env):
    m = game_env.module
    plot = m.plots[0]
    before = plot.value
    delta = plot.accrue_tick()
    assert delta > 0
    assert plot.value == before + delta


def test_accrue_tick_returns_zero_for_non_accruing_states(game_env):
    m = game_env.module
    m.plots[0].state = m.BARE
    assert m.plots[0].accrue_tick() == 0.0
