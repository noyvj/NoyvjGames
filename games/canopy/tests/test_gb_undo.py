"""GB-18: after Clear, a short Undo chip restores the plot (off in Ranger difficulty)."""


def _chip(env):
    return env.elements["undo-clear-button"]


def _snapshot(m, index):
    plot = m.plots[index]
    return (plot.state, plot.value, plot.ticks_intact, plot.clear_count, plot.biodiversity, plot.specialization)


def test_chip_is_hidden_until_a_clear(game_env):
    assert _chip(game_env).hidden is True
    game_env.select(0)
    assert _chip(game_env).hidden is True


def test_clear_shows_the_chip_with_an_accessible_label(game_env):
    game_env.tick(3)
    game_env.select(5)
    game_env.clear()
    chip = _chip(game_env)
    assert chip.hidden is False
    assert "Undo clear" in chip.innerText and "F1" in chip.innerText
    assert "Undo clearing F1" in chip.getAttribute("aria-label")


def test_undo_restores_the_plot_income_and_log(game_env):
    m = game_env.module
    game_env.tick(6)
    m.plots[5].specialization = None
    before = _snapshot(m, 5)
    income = m.total_income
    log_len = len(m.forest_log)
    game_env.select(5)
    game_env.clear()
    assert m.plots[5].state == m.BARE
    _chip(game_env).dispatch("click", None)
    assert _snapshot(m, 5) == before
    assert m.total_income == income
    assert not any(e["kind"] == "clear" for e in m.forest_log)
    assert len(m.forest_log) == log_len + 1  # the "took back the clear" note
    assert _chip(game_env).hidden is True


def test_undo_is_one_shot(game_env):
    m = game_env.module
    game_env.tick(3)
    game_env.select(5)
    game_env.clear()
    assert m.undo_last_clear() is True
    assert m.undo_last_clear() is False


def test_chip_lasts_three_to_four_seconds_then_goes(game_env):
    m = game_env.module
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    for _ in range(m.UNDO_WINDOW_TICKS):
        game_env.tick()
        assert _chip(game_env).hidden is False
    game_env.tick()
    assert _chip(game_env).hidden is True
    assert m.undo_last_clear() is False


def test_replanting_the_plot_invalidates_the_undo(game_env):
    m = game_env.module
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    game_env.replant()
    assert m.undo_last_clear() is False
    assert m.plots[5].state == m.REPLANTING


def test_a_new_clear_replaces_the_previous_undo(game_env):
    m = game_env.module
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    game_env.select(6)
    game_env.clear()
    assert m.undo_last_clear() is True
    assert m.plots[6].state != m.BARE
    assert m.plots[5].state == m.BARE


def test_no_undo_in_ranger_difficulty(game_env):
    m = game_env.module
    game_env.change_difficulty("ranger")
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    assert _chip(game_env).hidden is True
    assert m.undo_last_clear() is False
    assert m.plots[5].state == m.BARE


def test_a_granted_request_cannot_be_undone(game_env):
    m = game_env.module
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS + 1)
    assert m.pending_stakeholder_request is not None
    game_env.grant_stakeholder()
    assert _chip(game_env).hidden is True


def test_undoing_takes_back_the_income_record_and_streak_break(game_env):
    m = game_env.module
    game_env.tick(6)
    best_before = m.personal_best["income"]
    game_env.select(5)
    game_env.clear()
    assert m.personal_best["income"] > best_before and m.season_cleared is True
    m.undo_last_clear()
    assert m.personal_best["income"] == best_before
    assert m.season_cleared is False
    assert m.perfect_season_status()[0] is True


def test_undo_does_not_lower_a_record_set_earlier(game_env):
    m = game_env.module
    game_env.tick(6)
    game_env.select(5)
    game_env.clear()
    m.undo_last_clear()
    m.personal_best["income"] = 999.0
    game_env.select(6)
    game_env.clear()
    m.undo_last_clear()
    assert m.personal_best["income"] == 999.0


def test_undo_is_not_saved_and_reset_drops_it(game_env):
    m = game_env.module
    game_env.tick(2)
    game_env.select(5)
    game_env.clear()
    assert not any("undo" in key for key in m.get_state())
    game_env.reset_session()
    assert _chip(game_env).hidden is True
    assert m._undo_snapshot is None


def test_undo_chip_is_wired_and_a_button(game_env):
    assert len(_chip(game_env)._listeners["click"]) == 1
