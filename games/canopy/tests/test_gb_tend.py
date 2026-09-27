"""GB-4: Tend (hotkey T) gives one plot a short growth boost, then a 20-tick cooldown."""

from .gb_helpers import tile, tile_marks


def test_tend_boosts_growth_on_the_tended_plot_only(game_env):
    m = game_env.module
    game_env.tick(3)
    assert m.tend_plot(0) is True
    plot0, plot1 = m.plots[0], m.plots[1]
    v0, v1 = plot0.value, plot1.value
    game_env.tick()
    ratio = (plot0.value - v0) / (plot1.value - v1)
    assert abs(ratio - m.TEND_GROWTH_MULTIPLIER) < 1e-9


def test_boost_lasts_the_set_duration_then_a_cooldown_starts(game_env):
    m = game_env.module
    game_env.tick(2)
    m.tend_plot(0)
    assert m.plots[0].tend_ticks_left == m.TEND_DURATION_TICKS
    game_env.tick(m.TEND_DURATION_TICKS)
    assert m.plots[0].tend_ticks_left == 0
    assert m.tend_cooldown_ticks == m.TEND_COOLDOWN_TICKS


def test_cannot_tend_during_boost_or_cooldown_and_can_after(game_env):
    m = game_env.module
    m.tend_plot(0)
    assert m.tend_plot(1) is False  # a boost is running
    game_env.tick(m.TEND_DURATION_TICKS)
    assert m.tend_plot(1) is False  # cooling down
    game_env.tick(m.TEND_COOLDOWN_TICKS - 1)
    assert m.tend_plot(1) is False
    game_env.tick()
    assert m.tend_cooldown_ticks == 0
    assert m.tend_plot(1) is True


def test_cooldown_is_exactly_twenty_ticks_after_the_boost(game_env):
    m = game_env.module
    m.tend_plot(0)
    game_env.tick(m.TEND_DURATION_TICKS)
    remaining = []
    for _ in range(m.TEND_COOLDOWN_TICKS):
        remaining.append(m.tend_cooldown_ticks)
        game_env.tick()
    assert remaining[0] == 20 and remaining[-1] == 1 and m.tend_cooldown_ticks == 0


def test_a_bare_plot_cannot_be_tended(game_env):
    m = game_env.module
    game_env.select(3)
    game_env.clear()
    assert m.tend_plot(3) is False
    assert "replant" in m.tend_status_text()
    assert m.tend_cooldown_ticks == 0


def test_replanting_plot_recovers_an_extra_tick_per_tick(game_env):
    m = game_env.module
    game_env.select(3)
    game_env.clear()
    game_env.replant()
    m.tend_plot(3)
    game_env.tick()
    assert m.plots[3].replant_ticks_remaining == m.RECOVERY_TICKS - 2
    game_env.tick(3)
    assert m.plots[3].replant_ticks_remaining == m.RECOVERY_TICKS - 8


def test_tended_replant_can_finish_early_and_counts_the_recovery(game_env):
    m = game_env.module
    game_env.select(3)
    game_env.clear()
    game_env.replant()
    m.tend_plot(3)
    game_env.tick(5)
    assert m.plots[3].state == m.RECOVERED
    assert m.total_recoveries == 1


def test_tend_uses_the_selected_plot_without_an_index(game_env):
    m = game_env.module
    assert m.tend_plot() is False  # nothing selected
    assert "Hover or select" in m.tend_status_text()
    game_env.select(5)
    assert m.tend_plot() is True
    assert m.plots[5].tend_ticks_left == m.TEND_DURATION_TICKS


def test_bad_indices_are_rejected(game_env):
    m = game_env.module
    for bad in (-1, 999, True, "3", None, float("nan")):
        assert m.tend_plot(bad) is False
    assert m._tended_plot() is None


def test_button_state_and_label(game_env):
    m = game_env.module
    button = game_env.elements["tend-button"]
    assert button.disabled is True
    game_env.select(0)
    assert button.disabled is False and "Tend (T)" in button.innerText
    button.dispatch("click", None)
    assert m.plots[0].tend_ticks_left > 0
    assert button.disabled is True and "Tending" in button.innerText
    game_env.tick(m.TEND_DURATION_TICKS)
    assert str(m.TEND_COOLDOWN_TICKS) in button.innerText
    assert "recharging" in game_env.elements["tend-status"].innerText


def test_tile_is_marked_while_tended(game_env):
    m = game_env.module
    m.tend_plot(2)
    assert "plot-tended" in tile(game_env, 2).className
    assert "tend-mark" in tile_marks(game_env, 2)
    assert "tended" in tile(game_env, 2).getAttribute("aria-label")
    assert "plot-tended" not in tile(game_env, 3).className


def test_clearing_a_tended_plot_ends_the_boost(game_env):
    m = game_env.module
    m.tend_plot(0)
    game_env.select(0)
    game_env.clear()
    assert m.plots[0].tend_ticks_left == 0
    game_env.tick()
    assert m._tended_plot() is None


def test_tend_state_round_trips_and_is_absent_by_default(game_env):
    m = game_env.module
    assert "tend" not in m.get_state() and "tend_cooldown_ticks" not in m.get_state()
    m.tend_plot(4)
    game_env.tick(2)
    state = m.get_state()
    assert state["tend"] == {"plot": 4, "ticks_left": m.TEND_DURATION_TICKS - 2}
    m.load_state(state)
    assert m.plots[4].tend_ticks_left == m.TEND_DURATION_TICKS - 2
    game_env.tick(m.TEND_DURATION_TICKS - 2)
    assert m.get_state()["tend_cooldown_ticks"] == m.TEND_COOLDOWN_TICKS
    saved = m.get_state()
    m.tend_cooldown_ticks = 0
    m.load_state(saved)
    assert m.tend_cooldown_ticks == m.TEND_COOLDOWN_TICKS


def test_load_rejects_bad_tend_data(game_env):
    m = game_env.module
    base = m.get_state()
    for bad in ({"plot": 999, "ticks_left": 3}, {"plot": True, "ticks_left": 3}, {"plot": 0, "ticks_left": "x"},
                {"plot": 0, "ticks_left": 999}, [1, 2], "tend", 7):
        data = dict(base, tend=bad, tend_cooldown_ticks="soon")
        m.load_state(data)
        assert all(p.tend_ticks_left <= m.TEND_DURATION_TICKS for p in m.plots)
        assert m.tend_cooldown_ticks == 0


def test_reset_clears_tend(game_env):
    m = game_env.module
    m.tend_plot(0)
    game_env.tick(m.TEND_DURATION_TICKS)
    game_env.reset_session()
    assert m.tend_cooldown_ticks == 0 and m._tended_plot() is None


def test_load_state_clears_a_live_tend_the_save_lacks(game_env):
    m = game_env.module
    saved = m.get_state()
    m.tend_plot(0)
    m.load_state(saved)
    assert m._tended_plot() is None
