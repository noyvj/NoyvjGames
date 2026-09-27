"""GB-2: a golden seedling pops up on a bare or replanting plot for about 4
ticks; catching it banks a burst of recovery progress with the B4 leaf burst."""

from .gb_helpers import tile, tile_marks


def _bare(env, index):
    env.select(index)
    env.clear()


def _spawn(env, index):
    """Forces a seedling onto `index` (a bare plot) the way tick() would."""
    m = env.module
    m.golden_seedling = {"plot": index, "ticks_left": m.GOLDEN_SEEDLING_TICKS}
    m.render()


def test_no_seedling_when_nothing_is_bare_or_replanting(game_env):
    m = game_env.module
    m._golden_next_tick = 0
    game_env.tick(5)
    assert m.golden_seedling is None


def test_seedling_appears_on_a_bare_plot_once_due(game_env):
    m = game_env.module
    _bare(game_env, 4)
    m._golden_next_tick = 0
    game_env.tick()
    assert m.golden_seedling == {"plot": 4, "ticks_left": m.GOLDEN_SEEDLING_TICKS}


def test_seedling_can_appear_on_a_replanting_plot(game_env):
    m = game_env.module
    _bare(game_env, 4)
    game_env.replant()
    m._golden_next_tick = 0
    game_env.tick()
    assert m.golden_seedling["plot"] == 4


def test_seedling_lasts_about_four_ticks_then_is_rescheduled(game_env):
    m = game_env.module
    _bare(game_env, 4)
    m._golden_next_tick = 0
    game_env.tick()
    for expected_left in (3, 2, 1):
        game_env.tick()
        assert m.golden_seedling["ticks_left"] == expected_left
    game_env.tick()
    assert m.golden_seedling is None
    assert m._golden_next_tick >= m.forest_tick + m.GOLDEN_SEEDLING_MIN_GAP


def test_seedling_is_dropped_if_the_plot_recovered_meanwhile(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    m.plots[4].state = m.RECOVERED
    game_env.tick()
    assert m.golden_seedling is None


def test_spawn_is_deterministic_for_the_same_run(game_env):
    m = game_env.module
    for index in (1, 2, 3):
        _bare(game_env, index)
    m._golden_next_tick = 0
    game_env.tick()
    first = m.golden_seedling["plot"]
    assert first in (1, 2, 3)
    assert m._gb_hash(m.forest_tick, 5) % 3 == [1, 2, 3].index(first)


def test_tile_shows_the_seedling_with_a_label(game_env):
    _bare(game_env, 4)
    _spawn(game_env, 4)
    element = tile(game_env, 4)
    assert "plot-golden-seedling" in element.className
    assert "golden-seedling-mark" in tile_marks(game_env, 4)
    assert "golden seedling" in element.getAttribute("aria-label")
    assert "plot-golden-seedling" not in tile(game_env, 5).className


def test_clicking_the_tile_banks_recovery_on_a_bare_plot(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    replants = m.total_replants
    game_env.select_tile_click(4)
    plot = m.plots[4]
    assert plot.state == m.REPLANTING
    assert plot.replant_ticks_remaining == m.RECOVERY_TICKS - m.GOLDEN_SEEDLING_RECOVERY_TICKS
    assert m.total_replants == replants + 1
    assert m.golden_seedling is None


def test_clicking_banks_recovery_on_a_replanting_plot(game_env):
    m = game_env.module
    _bare(game_env, 4)
    game_env.replant()
    game_env.tick(2)
    before = m.plots[4].replant_ticks_remaining
    _spawn(game_env, 4)
    game_env.select_tile_click(4)
    assert m.plots[4].replant_ticks_remaining == before - m.GOLDEN_SEEDLING_RECOVERY_TICKS


def test_enough_progress_finishes_the_recovery(game_env):
    m = game_env.module
    _bare(game_env, 4)
    game_env.replant()
    game_env.tick(m.RECOVERY_TICKS - 2)
    assert m.plots[4].state == m.REPLANTING
    recoveries = m.total_recoveries
    _spawn(game_env, 4)
    game_env.select_tile_click(4)
    assert m.plots[4].state == m.RECOVERED
    assert m.total_recoveries == recoveries + 1


def test_catching_it_shows_a_leaf_burst_once(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    game_env.select_tile_click(4)
    marks = tile_marks(game_env, 4)
    assert sum(1 for c in marks if c.startswith("leaf-burst")) == m.LEAF_BURST_COUNT
    assert "plot-mature-burst" in tile(game_env, 4).className
    m.render()  # a later render must not replay it
    assert not any(c.startswith("leaf-burst") for c in tile_marks(game_env, 4))


def test_clicking_another_tile_does_not_catch_it(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    game_env.select_tile_click(5)
    assert m.golden_seedling is not None
    assert m.plots[4].state == m.BARE


def test_key_path_catches_without_an_index(game_env):
    m = game_env.module
    assert m.collect_golden_seedling() is False
    _bare(game_env, 4)
    _spawn(game_env, 4)
    assert m.collect_golden_seedling() is True
    assert m.plots[4].state == m.REPLANTING
    assert m.collect_golden_seedling() is False


def test_catching_is_logged(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    game_env.select_tile_click(4)
    assert any(e["kind"] == "golden" for e in m.forest_log)


def test_a_seedling_is_never_saved(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    assert "golden_seedling" not in m.get_state()
    m.load_state(m.get_state())
    assert m.golden_seedling is None


def test_reset_clears_the_seedling(game_env):
    m = game_env.module
    _bare(game_env, 4)
    _spawn(game_env, 4)
    game_env.reset_session()
    assert m.golden_seedling is None
