"""GG-23: the opt-in hard mode (no previews) with an end-of-run reveal of how close the forecasts were."""


def _forecast(game_env, value):
    game_env.elements["forecast-input"].value = str(value)
    game_env.elements["forecast-lock-button"].dispatch("click", None)


def test_off_by_default_and_previews_are_shown(game_env):
    m = game_env.module
    assert m.hard_mode is False
    assert game_env.elements["hard-mode-toggle-button"].innerText == "Hard mode: off"
    assert "Next round preview" in game_env.elements["advance-round-button"].title
    assert game_env.elements["preserve-forecast"].innerText
    assert "Right now" in game_env.elements["b-preset-growth-button"].title


def test_toggle_turns_off_every_preview(game_env):
    m = game_env.module
    game_env.elements["hard-mode-toggle-button"].dispatch("click", None)
    assert m.hard_mode is True
    assert game_env.elements["hard-mode-toggle-button"].innerText == "Hard mode: on"
    assert game_env.elements["advance-round-button"].title == "Hard mode: no preview of the next round."
    for name in ("output", "preserve", "monitor"):
        assert game_env.elements[f"{name}-forecast"].innerText == ""
    assert "Right now" not in game_env.elements["b-preset-growth-button"].title
    assert "Right now" not in game_env.elements["c-preset-balanced-button"].title
    assert "planner is switched off" in game_env.elements["planner-readout"].innerText
    assert game_env.elements["planner-chart"].innerHTML == ""


def test_the_numbers_the_player_reads_are_not_hidden(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    m.render()
    assert "Current warming rate" in game_env.elements["rise-rate-display"].innerText
    assert "Feedback dampening" in game_env.elements["dampening-display"].innerText
    assert game_env.elements["acceleration-display"].innerText


def test_only_before_round_one_and_it_locks_afterwards(game_env):
    m = game_env.module
    assert m.set_hard_mode(True) is True
    game_env.advance_round()
    assert m.set_hard_mode(False) is False
    assert m.hard_mode is True
    assert game_env.elements["hard-mode-toggle-button"].disabled is True
    assert "Locked" in game_env.elements["hard-mode-display"].innerText


def test_it_changes_no_game_numbers(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    for _ in range(6):
        game_env.invest("preserve")
        game_env.advance_round()
    hard = (m.region.temperature, m.region.funds, m.region.counterfactual_temperature)
    m.hard_mode = False
    # replay the same moves on a fresh region with hard mode off
    fresh = m.RegionState()
    for _ in range(6):
        fresh.invest("preserve")
        fresh.advance_round()
    assert hard == (fresh.temperature, fresh.funds, fresh.counterfactual_temperature)


def test_no_reveal_before_a_round_or_when_off(game_env):
    m = game_env.module
    assert m.hard_mode_reveal_lines() == []
    m.set_hard_mode(True)
    assert m.hard_mode_reveal_lines() == []  # round 1
    game_env.advance_round()
    assert len(m.hard_mode_reveal_lines()) == 1
    m.hard_mode = False
    assert m.hard_mode_reveal_lines() == []


def test_reveal_without_forecasts_points_at_the_forecast_box(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    game_env.advance_round()
    text = m.hard_mode_reveal_lines()[0]
    assert "did not lock in any forecast" in text and "forecast box" in text


def test_reveal_reports_the_average_miss(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    _forecast(game_env, 1.5)  # real figure will be 1.0, so a 0.5 miss
    game_env.advance_round()
    _forecast(game_env, 2.0)  # exact
    game_env.advance_round()
    assert m.forecast_total == 2 and m.forecast_hits == 1
    assert abs(m.forecast_miss_total - 0.5) < 1e-9
    text = m.hard_mode_reveal_lines()[0]
    assert "2 forecasts, 1 on target" in text and "0.2" in text  # an average of 0.25 shows as 0.2 or 0.3
    assert "close" in text


def test_reveal_wording_by_size_of_miss(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    game_env.advance_round()
    m.forecast_total, m.forecast_hits = 1, 1
    m.forecast_miss_total = 0.1
    assert "right on the money" in m.hard_mode_reveal_lines()[0]
    m.forecast_total, m.forecast_hits = 1, 0
    m.forecast_miss_total = 5.0
    assert "wide miss" in m.hard_mode_reveal_lines()[0]
    assert "1 forecast," in m.hard_mode_reveal_lines()[0]


def test_reveal_appears_in_the_recap_and_the_copy_text(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    game_env.advance_round()
    assert "hard-mode-reveal" in game_env.elements["highlights-list"].innerHTML
    assert "Hard mode reveal" in m.highlights_text()
    assert len(m.highlights_lines()) == 3  # the three-line recap itself is unchanged


def test_reveal_closes_a_hold_the_line_result(game_env):
    m = game_env.module
    m.set_hard_mode(True)
    m.set_hold_the_line(True)
    for _ in range(40):
        if m.run_over:
            break
        game_env.advance_round()
    assert m.run_over
    assert any("Hard mode reveal" in line for line in m.result_lines())


def test_it_works_with_the_long_game_and_hold_the_line(game_env):
    m = game_env.module
    assert m.set_hard_mode(True)
    assert m.set_long_game(True)
    assert m.set_hard_mode(True)


def test_saved_only_when_on_and_round_trips(game_env):
    m = game_env.module
    assert "hard_mode" not in m.get_state()
    m.set_hard_mode(True)
    _forecast(game_env, 3.0)
    game_env.advance_round()
    state = m.get_state()
    assert state["hard_mode"] is True
    assert state["forecast"]["miss"] > 0
    m.hard_mode = False
    m.forecast_miss_total = 0.0
    assert m.load_state(state)
    assert m.hard_mode is True
    assert abs(m.forecast_miss_total - state["forecast"]["miss"]) < 1e-6


def test_loading_a_save_without_it_turns_it_off(game_env):
    m = game_env.module
    state = m.get_state()
    m.set_hard_mode(True)
    assert m.load_state(state)
    assert m.hard_mode is False


def test_bad_saved_values_are_ignored(game_env):
    m = game_env.module
    base = m.get_state()
    assert m.load_state(dict(base, hard_mode="yes"))
    assert m.hard_mode is False
    bad_forecast = {"total": 2, "hits": 1, "miss": "lots"}
    assert m.load_state(dict(base, forecast=bad_forecast))
    assert m.forecast_miss_total == 0.0
    bad_forecast = {"total": 2, "hits": 1, "miss": float("inf")}
    assert m.load_state(dict(base, forecast=bad_forecast))
    assert m.forecast_miss_total == 0.0


def test_older_forecast_records_without_a_miss_still_load(game_env):
    m = game_env.module
    base = m.get_state()
    assert m.load_state(dict(base, forecast={"total": 3, "hits": 2}))
    assert m.forecast_total == 3 and m.forecast_miss_total == 0.0
