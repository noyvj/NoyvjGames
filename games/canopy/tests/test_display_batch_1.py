"""Canopy TODO batch: B6 (Highland progress bar), B8 (incentive tooltip),
B10 (biodiversity rate), B12 (soil hint), B14 (small grid), B20 (value-pop
size classes), B24 (reset confirm), B28 (counterfactual percentage)."""


# --- B6 -------------------------------------------------------------------

def test_highland_progress_bar_tracks_standing_value(game_env):
    m = game_env.module
    m.plots[0].value = 500.0
    m.render()
    bar = game_env.elements["highland-unlock-progress"]
    assert bar.hidden is False
    assert bar.max == m.HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD
    assert bar.value == 500.0


def test_highland_progress_bar_hides_once_unlocked(game_env):
    m = game_env.module
    for plot in m.plots:
        plot.value = 1000.0
    game_env.tick(1)
    assert m.highland_unlocked
    assert game_env.elements["highland-unlock-progress"].hidden is True


# --- B8 -------------------------------------------------------------------

def _raise_request(m, kind):
    m.pending_stakeholder_request = {
        "plot_index": 0, "reason": "ecotourism" if kind == "incentive" else "housing", "kind": kind,
    }
    m.plots[0].value = 10.0
    m.render()


def test_incentive_request_explains_it_is_positive(game_env):
    m = game_env.module
    _raise_request(m, "incentive")
    assert "positive" in game_env.elements["stakeholder-message"].title
    assert "standing" in game_env.elements["stakeholder-grant-button"].title
    assert "Incentive" in game_env.elements["stakeholder-badge"].innerText


def test_clear_request_has_plain_grant_tooltip_and_no_message_tooltip(game_env):
    m = game_env.module
    _raise_request(m, "clear")
    assert "clears the plot" in game_env.elements["stakeholder-grant-button"].title
    assert game_env.elements["stakeholder-message"].title == ""
    assert "Pending request" in game_env.elements["stakeholder-badge"].innerText


# --- B10 ------------------------------------------------------------------

def test_biodiversity_rate_counts_standing_plots(game_env):
    m = game_env.module
    assert m.biodiversity_rate_per_tick() == len(m.plots) * m.BIODIVERSITY_ACCRUAL_PER_TICK
    m.plots[0].clear()
    assert m.biodiversity_rate_per_tick() == (len(m.plots) - 1) * m.BIODIVERSITY_ACCRUAL_PER_TICK


def test_biodiversity_display_shows_rate(game_env):
    game_env.module.render()
    assert "/tick" in game_env.elements["biodiversity-display"].innerText


# --- B12 ------------------------------------------------------------------

def test_soil_hint_hidden_without_selection_and_shown_with_one(game_env):
    assert game_env.elements["soil-hint"].hidden is True
    game_env.select(0)
    hint = game_env.elements["soil-hint"]
    assert hint.hidden is False
    assert "100%" in hint.innerText
    assert "permanently" in hint.title


def test_soil_hint_reflects_degradation(game_env):
    m = game_env.module
    m.plots[0].clear_count = 3
    game_env.select(0)
    assert "70%" in game_env.elements["soil-hint"].innerText
    assert "70%" in game_env.elements["soil-hint"].title


# --- B14 ------------------------------------------------------------------

def test_small_grid_preset_is_4_by_4(game_env):
    game_env.change_grid_size("small")
    m = game_env.module
    assert (m.GRID_ROWS, m.GRID_COLS) == (4, 4)
    assert len(m.plots) == 16


def test_small_grid_save_round_trips(game_env):
    game_env.change_grid_size("small")
    m = game_env.module
    game_env.tick(3)
    state = m.get_state()
    game_env.change_grid_size("normal")
    m.load_state(state)
    assert len(m.plots) == 16


# --- B20 ------------------------------------------------------------------

def test_value_pop_size_class_scales_with_magnitude(game_env):
    m = game_env.module
    assert m._value_pop_size_class(1.0) == "value-pop--small"
    assert m._value_pop_size_class(m.VALUE_POP_MEDIUM_DELTA) == "value-pop--medium"
    assert m._value_pop_size_class(m.VALUE_POP_LARGE_DELTA + 1) == "value-pop--large"


# --- B24 ------------------------------------------------------------------

def test_reset_is_immediate_when_nothing_is_at_stake(game_env):
    m = game_env.module
    game_env.elements["reset-session-button"].dispatch("click", None)
    assert m._reset_confirm_armed is False


def test_reset_asks_first_and_names_what_is_given_up(game_env):
    m = game_env.module
    game_env.tick(5)
    standing = m.standing_forest_value()
    game_env.elements["reset-session-button"].dispatch("click", None)
    assert m._reset_confirm_armed is True
    assert f"{standing:.1f}" in game_env.elements["reset-session-button"].innerText
    assert m.standing_forest_value() == standing  # not reset yet


def test_second_click_confirms_reset(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.elements["reset-session-button"].dispatch("click", None)
    game_env.elements["reset-session-button"].dispatch("click", None)
    assert m.standing_forest_value() == 0.0
    assert m._reset_confirm_armed is False
    assert "Reset Session" in game_env.elements["reset-session-button"].innerText


def test_confirm_disarms_after_window(game_env):
    m = game_env.module
    game_env.tick(5)
    game_env.elements["reset-session-button"].dispatch("click", None)
    assert m._reset_confirm_armed
    game_env.timers.flush()
    assert m._reset_confirm_armed is False
    assert m.standing_forest_value() > 0


# --- B28 ------------------------------------------------------------------

def test_counterfactual_states_percentage_difference(game_env):
    m = game_env.module
    game_env.tick(10)
    m.plots[0].clear()
    for p in m.plots[:12]:
        p.value = 0.0
    text = m.counterfactual_message()
    assert "% of that" in text
    assert "% difference" in text
