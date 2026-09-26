"""B1 (planning/TODO.md "Per-game: Canopy"): a third region, Wetland Forest.
Same Plot class and clear/replant loop as Highland Grove, but it grows
faster and a flood sweeps it on a fixed timer -- much less damage to a
mature plot than a young one, silt on anything still replanting, and a
warning window before each flood."""


def _unlock(game_env):
    m = game_env.module
    m.highland_unlocked = True
    m.wetland_unlocked = True
    m.wetland_flood_countdown = m.WETLAND_FLOOD_INTERVAL_TICKS
    game_env.tick(1)


def test_wetland_starts_locked_and_hidden_until_highland_opens(game_env):
    m = game_env.module
    assert m.wetland_unlocked is False
    assert game_env.elements["wetland-section"].hidden is True
    assert game_env.elements["wetland-lock-banner"].hidden is True
    m.highland_unlocked = True
    m.render()
    assert game_env.elements["wetland-lock-banner"].hidden is False
    assert "locked" in game_env.elements["wetland-lock-banner"].innerText.lower()


def test_threshold_is_higher_than_highland(game_env):
    m = game_env.module
    assert m.WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD > m.HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD


def test_crossing_the_threshold_unlocks_it_permanently(game_env):
    m = game_env.module
    m.plots[0].value = m.WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD
    game_env.tick(1)
    assert m.wetland_unlocked is True
    assert game_env.elements["wetland-section"].hidden is False
    m.plots[0].value = 0.0
    game_env.tick(1)
    assert m.wetland_unlocked is True


def test_wetland_grows_faster_than_the_main_forest(game_env):
    m = game_env.module
    _unlock(game_env)
    m.plots[0].accrue_tick()
    m.wetland_plots[0].accrue_tick()
    assert m.wetland_plots[0].value > m.plots[0].value * 1.2


def test_flood_hits_young_plots_harder_than_mature_ones(game_env):
    m = game_env.module
    _unlock(game_env)
    young, mature = m.wetland_plots[0], m.wetland_plots[1]
    for other in m.wetland_plots[2:]:
        other.value = 0.0
    young.value = mature.value = 100.0
    young.ticks_intact = 5
    mature.ticks_intact = m.MATURITY_TICKS
    lost = m.apply_wetland_flood()
    assert young.value == 100.0 * (1 - m.WETLAND_FLOOD_LOSS_YOUNG)
    assert mature.value == 100.0 * (1 - m.WETLAND_FLOOD_LOSS_MATURE)
    assert abs(lost - 100.0 * (m.WETLAND_FLOOD_LOSS_YOUNG + m.WETLAND_FLOOD_LOSS_MATURE)) < 1e-9
    assert m.wetland_floods_survived == 1
    assert m.wetland_flood_value_lost == lost


def test_flood_silts_replanting_plots_but_capped_and_spares_bare_ones(game_env):
    m = game_env.module
    _unlock(game_env)
    bare, replanting = m.wetland_plots[0], m.wetland_plots[1]
    bare.state = m.BARE
    bare.value = 0.0
    replanting.state = m.REPLANTING
    replanting.replant_ticks_remaining = m.RECOVERY_TICKS - 2
    m.apply_wetland_flood()
    assert bare.state == m.BARE and bare.value == 0.0
    assert replanting.replant_ticks_remaining == m.RECOVERY_TICKS


def test_flood_fires_on_the_countdown_and_resets_it(game_env):
    m = game_env.module
    _unlock(game_env)
    m.wetland_flood_countdown = 2
    game_env.tick(1)
    assert m.wetland_floods_survived == 0 and m.wetland_flood_countdown == 1
    game_env.tick(1)
    assert m.wetland_floods_survived == 1
    assert m.wetland_flood_countdown == m.WETLAND_FLOOD_INTERVAL_TICKS
    assert any(e["kind"] == "flood" for e in m.forest_log)


def test_warning_window_is_flagged_and_highlights_young_plots(game_env):
    m = game_env.module
    _unlock(game_env)
    m.wetland_flood_countdown = m.WETLAND_FLOOD_WARNING_TICKS + 1
    m.wetland_plots[0].ticks_intact = 3
    m.render()
    assert "Next flood" in game_env.elements["wetland-flood-status"].innerText
    assert "plot-flood-risk" not in game_env.elements["wetland-plot-0"].className
    m.wetland_flood_countdown = m.WETLAND_FLOOD_WARNING_TICKS
    m.render()
    assert "Flood warning" in game_env.elements["wetland-flood-status"].innerText
    assert "plot-flood-risk" in game_env.elements["wetland-plot-0"].className


def test_harvesting_before_the_flood_banks_the_value(game_env):
    m = game_env.module
    _unlock(game_env)
    plot = m.wetland_plots[0]
    plot.value = 80.0
    plot.ticks_intact = 3
    game_env.elements["wetland-plot-0"].dispatch("click", None)
    game_env.elements["wetland-clear-button"].dispatch("click", None)
    assert m.wetland_income == 80.0
    assert plot.state == m.BARE and plot.value == 0.0
    before = m.wetland_flood_value_lost
    m.apply_wetland_flood()
    assert m.wetland_flood_value_lost - before < 80.0  # the banked 80 is out of the water's reach


def test_replant_button_works(game_env):
    m = game_env.module
    _unlock(game_env)
    m.wetland_plots[2].state = m.BARE
    game_env.elements["wetland-plot-2"].dispatch("click", None)
    game_env.elements["wetland-replant-button"].dispatch("click", None)
    assert m.wetland_plots[2].state == m.REPLANTING


def test_save_round_trip_keeps_the_wetland(game_env):
    m = game_env.module
    _unlock(game_env)
    m.wetland_plots[3].value = 42.0
    m.wetland_income = 7.0
    m.wetland_flood_countdown = 17
    m.wetland_floods_survived = 2
    m.wetland_flood_value_lost = 12.5
    m.wetland_selected_index = 3
    state = m.get_state()
    m.reset_session()
    assert m.wetland_unlocked is False
    assert m.load_state(state) is True
    assert m.wetland_unlocked is True
    assert m.wetland_plots[3].value == 42.0
    assert (m.wetland_income, m.wetland_flood_countdown, m.wetland_floods_survived) == (7.0, 17, 2)
    assert m.wetland_flood_value_lost == 12.5 and m.wetland_selected_index == 3


def test_save_omits_wetland_keys_until_unlocked(game_env):
    state = game_env.module.get_state()
    assert not [k for k in state if k.startswith("wetland_")]


def test_loading_a_save_without_wetland_clears_the_live_wetland(game_env):
    m = game_env.module
    old = m.get_state()
    _unlock(game_env)
    m.wetland_plots[0].value = 50.0
    assert m.load_state(old) is True
    assert m.wetland_unlocked is False
    assert m.wetland_plots[0].value == 0.0
    assert game_env.elements["wetland-section"].hidden is True


def test_corrupt_wetland_fields_fall_back_safely(game_env):
    m = game_env.module
    _unlock(game_env)
    state = m.get_state()
    state["wetland_flood_countdown"] = True
    state["wetland_income"] = "lots"
    state["wetland_floods_survived"] = -4
    state["wetland_selected_index"] = 999
    state["wetland_flood_value_lost"] = float("nan")
    state["wetland_plots"] = "nope"
    assert m.load_state(state) is True
    assert m.wetland_flood_countdown == m.WETLAND_FLOOD_INTERVAL_TICKS
    assert m.wetland_income == 0.0
    assert m.wetland_floods_survived == 0
    assert m.wetland_selected_index is None
    assert m.wetland_flood_value_lost == 0.0
    game_env.tick(3)


def test_countdown_out_of_range_is_clamped(game_env):
    m = game_env.module
    _unlock(game_env)
    state = m.get_state()
    state["wetland_flood_countdown"] = 10 ** 6
    m.load_state(state)
    assert m.wetland_flood_countdown == m.WETLAND_FLOOD_INTERVAL_TICKS
    state["wetland_flood_countdown"] = -5
    m.load_state(state)
    assert m.wetland_flood_countdown == 1


def test_reset_session_relocks_the_wetland(game_env):
    m = game_env.module
    _unlock(game_env)
    m.wetland_income = 9.0
    m.reset_session()
    assert m.wetland_unlocked is False
    assert m.wetland_income == 0.0
    assert m.wetland_floods_survived == 0
    assert m.wetland_flood_countdown == m.WETLAND_FLOOD_INTERVAL_TICKS
