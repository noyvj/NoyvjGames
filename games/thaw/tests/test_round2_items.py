"""Round-2 Thaw items: G2/G4/G6/G8/G10/G12/G14/G16/G18/G19/G20/G22/G24/G26/G28/G30."""


def _advance(env, n):
    for _ in range(n):
        env.advance_round()


def test_trend_none_then_flat_then_up(game_env):
    r = game_env.region
    assert r.temperature_trend() is None
    _advance(game_env, 2)
    assert r.temperature_trend() == "flat"
    _advance(game_env, 12)  # past melt threshold -> rise accelerates
    assert r.temperature_trend() == "up"
    assert game_env.elements["temperature-trend"].innerText == "▲"


def test_trend_down_with_dampening_investment(game_env):
    r = game_env.region
    r.temperature = 11.0
    r.temperature_history = [9.0, 11.0]
    r.capacity["preserve"] = 10
    r.advance_round()  # dampened rise is smaller than the previous rise of 2.0
    assert r.temperature_trend() == "down"


def test_streak_counts_and_resets_on_melt(game_env):
    r = game_env.region
    _advance(game_env, 5)
    assert r.tipping_events == 0 and r.rounds_since_tipping_event == 5
    assert "5 rounds stable" in game_env.elements["tipping-streak-display"].innerText
    _advance(game_env, 5)
    assert r.tipping_events >= 1
    assert r.rounds_since_tipping_event < 5


def test_critical_pulse_flag_fires_once(game_env):
    r = game_env.region
    r.temperature = 16.0
    r.melt_started_round = 5
    r.advance_round()
    assert "critical" in r.round_events
    game_env.module.render()
    assert "acceleration-pulse" in game_env.elements["acceleration-display"].className
    game_env.module.render()
    assert "acceleration-pulse" not in game_env.elements["acceleration-display"].className


def test_preemptive_callout_only_with_dampening(game_env):
    r = game_env.region
    r.temperature = 9.5
    r.advance_round()
    assert r.just_preempted_melt is False
    r2 = game_env.module.region_b
    r2.capacity["preserve"] = 4
    r2.temperature = 9.5
    r2.advance_round()
    assert r2.just_preempted_melt is True
    r.temperature = 9.5
    r.melt_started_round = None
    r.capacity["preserve"] = 4
    r.advance_round()
    game_env.module.render()
    assert not game_env.elements["preemptive-callout"].hidden
    assert "32%" in game_env.elements["preemptive-callout"].innerText
    game_env.module.render()
    assert game_env.elements["preemptive-callout"].hidden


def test_intervention_message_tier_icons(game_env):
    r = game_env.region
    r.capacity["preserve"] = 1
    assert "\U0001F331" in r.intervention_feedback_message()
    r.capacity["preserve"] = 5
    assert "\U0001F6E1" in r.intervention_feedback_message()
    r.capacity["preserve"] = 10
    assert "\U0001F3F0" in r.intervention_feedback_message()


def test_graph_threshold_label(game_env):
    svg = game_env.module.mini_temp_graph_svg([2.0, 8.0, 14.0])
    assert "mini-temp-threshold-label" in svg and "+10" in svg
    assert "mini-temp-threshold-label" not in game_env.module.mini_temp_graph_svg([1.0, 2.0])


def test_preset_preview_does_not_spend(game_env):
    m = game_env.module
    before = m.region_b.funds
    text = m.preset_preview_text(m.region_b, "growth")
    assert "Output" in text and m.region_b.funds == before
    m.region_b.funds = 5
    assert "not enough" in m.preset_preview_text(m.region_b, "growth")
    game_env.module.render()
    assert "Right now" in game_env.elements["b-preset-growth-button"].title


def test_advance_tooltip_combines_three_regions(game_env):
    title = game_env.elements["advance-round-button"].title
    assert title.count("Region") == 3 and "\n" in title


def test_science_log_records_and_caps(game_env):
    m = game_env.module
    _advance(game_env, 12)
    assert any("began melting" in e["text"] for e in m.science_log)
    assert game_env.elements["science-log-count"].innerText == str(len(m.science_log))
    assert "Region A" in game_env.elements["science-log-list"].innerHTML
    m.science_log.extend({"region": "A", "round": 1, "text": "x"} for _ in range(100))
    game_env.advance_round()
    assert len(m.science_log) <= m.SCIENCE_LOG_MAX


def test_science_log_round_trips_and_tolerates_junk(game_env):
    m = game_env.module
    _advance(game_env, 12)
    state = m.get_state()
    m.science_log.clear()
    m.load_state(state)
    assert len(m.science_log) == len(state["science_log"]) > 0
    m.load_state({"science_log": [1, {"round": "x"}, {"region": "B", "round": 3, "text": "<b>"}]})
    assert m.science_log[-1]["text"] == "<b>"
    assert "&lt;b&gt;" in game_env.elements["science-log-list"].innerHTML


def test_old_save_without_new_fields_loads(game_env):
    m = game_env.module
    assert m.load_state({"region": {"round_number": 4, "temperature": 3.0}})
    assert m.region.tipping_events == 0


def test_personal_best_tracks_region(game_env):
    m = game_env.module
    m.region_b.capacity["preserve"] = 10
    m.region_b.temperature = 20.0
    m.region_b.counterfactual_temperature = 30.0
    m._maybe_update_personal_best()
    assert m.personal_best["region"] == "B"
    m.render_personal_best()
    assert "(Region B)" in game_env.elements["personal-best-display"].innerText


def test_worst_case_intro_note_shows_once(game_env):
    note = game_env.elements["d-intro-note"]
    assert note.hidden
    game_env.toggle_worst_case_region()
    assert not note.hidden
    game_env.toggle_worst_case_region()  # close
    game_env.toggle_worst_case_region()  # reopen
    assert note.hidden
    assert game_env.module.get_state()["worst_case_intro_seen"] is True
    assert "automated" in game_env.elements["worst-case-toggle-button"].title


def test_best_region_message_names_winning_investment_mix(game_env):
    m = game_env.module
    m.region_b.capacity["preserve"] = 3
    m.region_b.capacity["monitor"] = 1
    m.region_b.capacity["output"] = 2
    m.region_b.temperature = -5.0
    label = m.best_region_identifier()
    assert label == "B"
    msg = m.best_region_message()
    assert "Region B" in msg
    assert "3 preserve / 1 monitor / 2 output" in msg
