"""GG-17: one rewind per run."""


def _play(game_env, rounds):
    for _ in range(rounds):
        game_env.advance_round()


def _rewind(game_env):
    game_env.elements["undo-button"].dispatch("click")


def test_unavailable_before_the_first_round(game_env):
    assert game_env.elements["undo-button"].disabled is True
    assert "after your first Advance Round" in game_env.elements["undo-display"].innerText


def test_available_after_a_round_and_restores_the_state(game_env):
    m = game_env.module
    game_env.invest("preserve")
    before = m.get_state()
    game_env.advance_round()
    assert game_env.elements["undo-button"].disabled is False
    _rewind(game_env)
    assert m.region.round_number == 1
    assert m.region.temperature == 0.0
    assert m.region.capacity["preserve"] == 1
    after = m.get_state()
    before["region"]["funds"] -= m.UNDO_COST
    after.pop("undo_used")
    assert after == before


def test_costs_funds_from_region_a_only(game_env):
    m = game_env.module
    game_env.invest("output")
    funds = (m.region.funds, m.region_b.funds, m.region_c.funds)
    game_env.advance_round()
    _rewind(game_env)
    assert m.region.funds == funds[0] - m.UNDO_COST
    assert (m.region_b.funds, m.region_c.funds) == funds[1:]


def test_only_once_per_run(game_env):
    m = game_env.module
    _play(game_env, 2)
    _rewind(game_env)
    assert m.undo_used is True
    assert game_env.elements["undo-button"].disabled is True
    game_env.advance_round()
    assert game_env.elements["undo-button"].disabled is True
    assert m.undo_last_round() is False
    assert "Rewind used" in game_env.elements["undo-button"].innerText


def test_needs_the_funds_in_region_a(game_env):
    m = game_env.module
    m.region.funds = 10
    game_env.advance_round()
    assert m.can_undo() is False
    assert game_env.elements["undo-button"].disabled is True
    assert "did not have that much" in m.undo_text()
    assert m.undo_last_round() is False
    assert m.region.round_number == 2


def test_flag_is_saved_only_once_used_and_survives_a_reload(game_env):
    m = game_env.module
    assert "undo_used" not in m.get_state()
    _play(game_env, 2)
    _rewind(game_env)
    state = m.get_state()
    assert state["undo_used"] is True
    m.undo_used = False
    m.load_state(state)
    assert m.undo_used is True


def test_old_or_bad_values_load_as_unused(game_env):
    m = game_env.module
    for bad in (None, 1, "yes", [True]):
        m.load_state({"undo_used": bad})
        assert m.undo_used is False


def test_loading_a_save_clears_the_snapshot(game_env):
    m = game_env.module
    game_env.advance_round()
    assert m._undo_snapshot is not None
    m.load_state(m.get_state())
    assert m._undo_snapshot is None
    assert game_env.elements["undo-button"].disabled is True


def test_rewind_restores_the_log_and_pins(game_env):
    m = game_env.module
    _play(game_env, 9)
    m.science_log.append({"region": "A", "round": 9, "text": "x", "pinned": True})
    m.render()
    game_env.advance_round()  # melt starts around round 10
    count_after = len(m.science_log)
    _rewind(game_env)
    assert len(m.science_log) <= count_after
    assert any(e.get("pinned") for e in m.science_log)


def test_interface_choices_are_kept(game_env):
    m = game_env.module
    game_env.advance_round()
    game_env.toggle_worst_case_region()
    game_env.set_strategy_label("b", "new label")
    _rewind(game_env)
    assert m.worst_case_region_revealed is True
    assert m.region_b.strategy_label == "new label"
    assert game_env.elements["b-strategy-label-input"].value == "new label"


def test_cannot_rewind_a_finished_run(game_env):
    m = game_env.module
    m.set_hold_the_line(True)
    for r in (m.region, m.region_b, m.region_c):
        r.temperature = 40.0
    game_env.advance_round()
    assert m.run_over is True
    assert game_env.elements["undo-button"].disabled is True
    assert m.undo_last_round() is False
    assert "nothing to rewind" in m.undo_text()


def test_forecast_record_goes_back_with_the_round(game_env):
    m = game_env.module
    game_env.elements["forecast-input"].value = "1.0"
    game_env.elements["forecast-lock-button"].dispatch("click")
    game_env.advance_round()
    assert m.forecast_total == 1
    _rewind(game_env)
    assert m.forecast_total == 0
    assert m.region.round_number == 1


def test_rewound_game_replays_identically(game_env):
    m = game_env.module
    _play(game_env, 4)
    temp_first = m.region.temperature
    state_before = m.region.round_number
    _rewind(game_env)
    assert m.region.round_number == state_before - 1
    game_env.advance_round()
    assert m.region.temperature == temp_first
