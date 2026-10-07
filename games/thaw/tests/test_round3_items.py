"""Round-3 TODO batch: GG-5 resource routing, GG-27 perfect-balance bonus, GG-13 Ice Age medal,
GG-20 "phew" callout, GG-28 highlights recap, G-4 explain-this-number, G-24 acceleration sparkline
and G-10 screen-reader support (aria-live round summary, graph summaries)."""

import math


def _melting(r, temperature, round_number=5):
    r.temperature = temperature
    r.counterfactual_temperature = temperature
    r.melt_started_round = 1
    r.round_number = round_number


def _select(env, element_id, value):
    env.elements[element_id].value = value
    env.elements[element_id].dispatch("change", None)


# --------------------------------------------------------------------------- GG-5 routing
def test_convoy_moves_funds_minus_tax(game_env):
    m = game_env.module
    m.region.funds, m.region_b.funds = 200.0, 100.0
    assert m.route_funds("a", "b") is True
    assert m.region.funds == 150.0
    assert m.region_b.funds == 100.0 + 50.0 * (1 - m.ROUTING_TAX)
    assert m.convoys_sent == 1
    assert math.isclose(m.convoy_tax_lost, 50.0 * m.ROUTING_TAX)


def test_convoy_refused_when_invalid(game_env):
    m = game_env.module
    m.region.funds = 49.0
    assert m.route_funds("a", "b") is False  # too poor
    m.region.funds = 500.0
    assert m.route_funds("a", "a") is False  # same region
    assert m.route_funds("a", "d") is False  # Region D can't take part
    assert m.route_funds("x", "b") is False
    assert m.convoys_sent == 0 and m.region.funds == 500.0


def test_convoy_never_touches_region_d(game_env):
    m = game_env.module
    d_before = (m.region_d.funds, m.region_d.temperature)
    m.region.funds = 300.0
    m.route_funds("a", "c")
    assert (m.region_d.funds, m.region_d.temperature) == d_before


def test_routing_ui_sends_a_convoy(game_env):
    m = game_env.module
    _select(game_env, "routing-source", "a")
    _select(game_env, "routing-dest", "c")
    button = game_env.elements["routing-send-button"]
    assert button.disabled is False and "A" in button.innerText and "C" in button.innerText
    button.dispatch("click", None)
    assert m.convoys_sent == 1
    assert m.region_c.funds == 300.0 + 40.0
    assert "Convoys sent: 1" in game_env.elements["routing-display"].innerText


def test_routing_button_disabled_when_source_cannot_afford(game_env):
    m = game_env.module
    m.region.funds = 10.0
    _select(game_env, "routing-source", "a")
    _select(game_env, "routing-dest", "b")
    assert game_env.elements["routing-send-button"].disabled is True
    assert "only 10 funds" in game_env.elements["routing-preview"].innerText


def test_routing_preview_states_the_tax(game_env):
    _select(game_env, "routing-dest", "b")
    text = game_env.elements["routing-preview"].innerText
    assert "50 funds" in text and "40" in text and "20%" in text


def test_routing_save_round_trip_and_defaults(game_env):
    m = game_env.module
    assert "routing" not in m.get_state()
    m.route_funds("a", "b")
    state = m.get_state()
    assert state["routing"] == {"convoys": 1, "tax_lost": 10.0}
    m.convoys_sent, m.convoy_tax_lost = 0, 0.0
    m.load_state(state)
    assert m.convoys_sent == 1 and m.convoy_tax_lost == 10.0


def test_routing_load_rejects_bad_values(game_env):
    m = game_env.module
    for bad in ({"convoys": True, "tax_lost": 1}, {"convoys": -1, "tax_lost": 1},
                {"convoys": 2, "tax_lost": float("nan")}, {"convoys": 2}, "x", None):
        m.load_state({"routing": bad})
        assert m.convoys_sent == 0 and m.convoy_tax_lost == 0.0


# --------------------------------------------------------------------------- GG-27 balance
def test_no_balance_bonus_before_melt(game_env):
    m = game_env.module
    assert m.regions_balanced() is False
    assert m.apply_balance_bonus() is False
    assert m.balance_bonuses == 0


def test_balance_bonus_when_all_melting_and_close(game_env):
    m = game_env.module
    for r, t in ((m.region, 12.0), (m.region_b, 12.4), (m.region_c, 12.9)):
        _melting(r, t)
    funds = [r.funds for r in (m.region, m.region_b, m.region_c)]
    assert m.apply_balance_bonus() is True
    assert [r.funds for r in (m.region, m.region_b, m.region_c)] == [f + m.BALANCE_BONUS_FUNDS for f in funds]
    assert m.balance_bonuses == 1


def test_no_balance_bonus_when_spread_too_wide(game_env):
    m = game_env.module
    for r, t in ((m.region, 12.0), (m.region_b, 12.4), (m.region_c, 13.5)):
        _melting(r, t)
    assert m.apply_balance_bonus() is False


def test_no_balance_bonus_when_one_region_not_melting(game_env):
    m = game_env.module
    _melting(m.region, 12.0)
    _melting(m.region_b, 12.0)
    m.region_c.temperature = 9.5
    assert m.regions_balanced() is False


def test_balance_bonus_through_advance_round_pulses_and_logs(game_env):
    m = game_env.module
    for r in (m.region, m.region_b, m.region_c):
        _melting(r, 12.0)
    game_env.advance_round()
    assert m.balance_bonuses == 1
    assert game_env.elements["balance-callout"].hidden is False
    assert "balance-pulse" in game_env.elements["region-comparison"].className
    assert "Perfect-balance bonuses: 1" in game_env.elements["balance-display"].innerText
    assert any(e["region"] == "ABC" for e in m.science_log)
    game_env.module.render()  # the pulse is a one-tick cue
    assert game_env.elements["balance-callout"].hidden is True
    assert "balance-pulse" not in game_env.elements["region-comparison"].className


def test_balance_bonus_leaves_region_d_alone(game_env):
    m = game_env.module
    for r in (m.region, m.region_b, m.region_c):
        _melting(r, 12.0)
    d_funds = m.region_d.funds
    m.apply_balance_bonus()
    assert m.region_d.funds == d_funds


def test_balance_save_round_trip(game_env):
    m = game_env.module
    assert "balance_bonuses" not in m.get_state()
    m.balance_bonuses = 3
    state = m.get_state()
    m.balance_bonuses = 0
    m.load_state(state)
    assert m.balance_bonuses == 3
    m.load_state({"balance_bonuses": True})
    assert m.balance_bonuses == 0


def test_science_log_accepts_abc_label_on_load(game_env):
    m = game_env.module
    m.load_state({"science_log": [{"region": "ABC", "round": 4, "text": "x"}]})
    assert m.science_log[0]["region"] == "ABC"


# --------------------------------------------------------------------------- GG-13 Ice Age
def test_ice_age_tier_function(game_env):
    m = game_env.module
    assert m.ice_age_tier(0) is None and m.ice_age_tier(4) is None
    assert m.ice_age_tier(5)[1] == "Frost"
    assert m.ice_age_tier(10)[1] == "Glacier"
    assert m.ice_age_tier(14)[1] == "Glacier"
    assert m.ice_age_tier(15)[1] == "Ice Age"
    assert m.ice_age_tier(99)[1] == "Ice Age"


def test_streak_grows_each_quiet_round_and_tracks_best(game_env):
    m = game_env.module
    for _ in range(6):
        game_env.advance_round()
    assert m.region.rounds_since_tipping_event == 6
    assert m.region.best_stable_streak == 6
    assert "Frost medal" in game_env.elements["ice-age-display"].innerText


def test_best_streak_survives_a_tipping_event(game_env):
    m = game_env.module
    for _ in range(12):  # melt starts at +10 on round 10, which resets the streak
        game_env.advance_round()
    assert m.region.best_stable_streak == 9
    assert m.region.rounds_since_tipping_event < 9
    assert "Best so far" in game_env.elements["ice-age-display"].innerText


def test_ice_age_text_names_next_tier_and_top_medal(game_env):
    m = game_env.module
    m.region.rounds_since_tipping_event = 7
    m.region.best_stable_streak = 7
    assert "Next: " in m.ice_age_text(m.region) and "Glacier" in m.ice_age_text(m.region)
    m.region.rounds_since_tipping_event = m.region.best_stable_streak = 15
    assert "The top medal" in m.ice_age_text(m.region)


def test_best_streak_save_round_trip_and_old_save(game_env):
    m = game_env.module
    m.region.best_stable_streak = 8
    state = m.get_state()
    assert state["region"]["best_stable_streak"] == 8
    m.region.best_stable_streak = 0
    m.load_state(state)
    assert m.region.best_stable_streak == 8
    old = m.get_state()
    del old["region"]["best_stable_streak"]
    m.region.rounds_since_tipping_event = 3
    old["region"]["rounds_since_tipping_event"] = 3
    m.load_state(old)
    assert m.region.best_stable_streak == 3
    old["region"]["best_stable_streak"] = True
    m.load_state(old)
    assert m.region.best_stable_streak == 3


# --------------------------------------------------------------------------- GG-20 phew
def _headed_critical(r):
    r.temperature = 15.0
    r.melt_started_round = 1
    r.capacity["preserve"] = 0
    r.funds = 500.0


def test_projection_is_critical_before_the_investment(game_env):
    m = game_env.module
    _headed_critical(m.region)
    assert m.region.projected_next_acceleration() >= m.CRITICAL_ACCELERATION_FACTOR


def test_investment_that_pulls_region_back_sets_flag(game_env):
    m = game_env.module
    _headed_critical(m.region)
    m.region.invest("preserve")
    assert m.region.just_pulled_back is True
    assert m.region.projected_next_acceleration() < m.CRITICAL_ACCELERATION_FACTOR


def test_output_investment_never_triggers_phew(game_env):
    m = game_env.module
    _headed_critical(m.region)
    m.region.invest("output")
    assert m.region.just_pulled_back is False


def test_no_phew_when_not_headed_for_critical(game_env):
    m = game_env.module
    m.region.funds = 500.0
    m.region.invest("preserve")
    assert m.region.just_pulled_back is False


def test_no_phew_when_investment_is_not_enough(game_env):
    m = game_env.module
    m.region.temperature = 30.0
    m.region.melt_started_round = 1
    m.region.funds = 500.0
    m.region.invest("monitor")
    assert m.region.projected_next_acceleration() >= m.CRITICAL_ACCELERATION_FACTOR
    assert m.region.just_pulled_back is False


def test_phew_callout_renders_once_and_names_the_region(game_env):
    m = game_env.module
    _headed_critical(m.region_b)
    game_env.invest_secondary("b", "preserve")
    callout = game_env.elements["phew-callout"]
    assert callout.hidden is False and "Phew" in callout.innerText and "Region B" in callout.innerText
    m.render()
    assert callout.hidden is True


def test_rescue_can_trigger_phew(game_env):
    m = game_env.module
    _headed_critical(m.region)
    m.region.temperature = 18.0
    assert m.region.is_critical()
    m.region.rescue()
    assert m.region.just_pulled_back is True


def test_phew_flag_is_not_saved(game_env):
    m = game_env.module
    _headed_critical(m.region)
    m.region.invest("preserve")
    assert "just_pulled_back" not in m.get_state()["region"]
    m.load_state(m.get_state())
    assert m.region.just_pulled_back is False


# --------------------------------------------------------------------------- GG-28 recap
def test_highlights_with_nothing_happened(game_env):
    lines = game_env.module.highlights_lines()
    assert len(lines) == 3
    assert "No region has tipped" in lines[0]
    assert "no region has needed" in lines[1]
    assert "Degrees saved" in lines[2]


def test_highlights_name_when_each_region_tipped(game_env):
    m = game_env.module
    m.region.melt_started_round = 9
    m.region_c.melt_started_round = 12
    first = m.highlights_lines()[0]
    assert "Region A tipped in round 9" in first and "Region C tipped in round 12" in first
    assert "Region B" not in first


def test_highlights_report_restoration_and_rescue(game_env):
    m = game_env.module
    m.region_b.restored_total = 1.5
    assert "restoration pulled back 1.5" in m.highlights_lines()[1]
    m.region_b.restored_total = 0.0
    m.region_c.rescue_used = True
    assert "Region C used its one emergency rescue" in m.highlights_lines()[1]


def test_highlights_render_three_list_items(game_env):
    game_env.module.render()
    assert game_env.elements["highlights-list"].innerHTML.count("<li>") == 3


def test_highlights_copy_falls_back_without_a_clipboard(game_env):
    game_env.elements["highlights-copy-button"].dispatch("click", None)
    assert "isn't available" in game_env.elements["highlights-status"].innerText


def test_highlights_copy_writes_to_the_clipboard(game_env):
    import sys
    import types

    written = []
    clipboard = types.SimpleNamespace(writeText=lambda text: written.append(text))
    sys.modules["js"].navigator = types.SimpleNamespace(clipboard=clipboard)
    game_env.elements["highlights-copy-button"].dispatch("click", None)
    assert written and written[0].startswith("Thaw highlights")
    assert game_env.elements["highlights-status"].innerText == "Copied to the clipboard."


# --------------------------------------------------------------------------- G-24 sparkline
def test_acceleration_history_grows_one_per_round(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    assert len(m.region.acceleration_history) == 3
    assert all(v >= 1.0 for v in m.region.acceleration_history)


def test_acceleration_history_is_capped(game_env):
    m = game_env.module
    m.region.funds = 0.0
    for _ in range(m.ACCEL_HISTORY_MAX + 6):
        m.region.advance_round()
    assert len(m.region.acceleration_history) == m.ACCEL_HISTORY_MAX


def test_sparkline_empty_until_two_points(game_env):
    m = game_env.module
    assert m.accel_sparkline_svg([]) == "" and m.accel_sparkline_svg([1.2]) == ""
    assert "after the second round" in m.accel_sparkline_text([1.0])


def test_sparkline_svg_has_line_and_text_alternative(game_env):
    svg = game_env.module.accel_sparkline_svg([1.0, 1.0, 1.5, 2.2])
    assert "accel-sparkline-line" in svg and 'role="img"' in svg
    assert "from 1.0x to 2.2x, rising; peak 2.2x" in svg


def test_sparkline_text_directions(game_env):
    m = game_env.module
    assert "falling" in m.accel_sparkline_text([2.0, 1.5])
    assert "steady" in m.accel_sparkline_text([1.5, 1.5])


def test_sparkline_rendered_into_status_block(game_env):
    for _ in range(2):
        game_env.advance_round()
    assert "accel-sparkline-svg" in game_env.elements["acceleration-sparkline"].innerHTML


def test_acceleration_history_save_round_trip_and_validation(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    state = m.get_state()
    saved = list(m.region.acceleration_history)
    m.region.acceleration_history = []
    m.load_state(state)
    assert m.region.acceleration_history == saved
    state["region"]["acceleration_history"] = [1.0, True, float("nan"), -2, "x", 1.5]
    m.load_state(state)
    assert m.region.acceleration_history == [1.0, 1.5]
    state["region"]["acceleration_history"] = "bad"
    m.load_state(state)
    assert m.region.acceleration_history == []


# --------------------------------------------------------------------------- G-4 inspector
def test_breakdown_adds_up_to_the_live_rate(game_env):
    m = game_env.module
    m.region.temperature = 14.0
    m.region.capacity["preserve"] = 3
    m.region.capacity["monitor"] = 2
    b = m.rate_breakdown(m.region)
    assert math.isclose(b["total"], m.region.current_rise_rate())
    assert math.isclose(b["acceleration"], m.region.acceleration_factor())
    cut = b["preserve"] + b["monitor"] + b["stance"] + b["rescue"]
    assert math.isclose(b["raw_feedback"] - cut, b["net_feedback"])


def test_breakdown_splits_levers_in_proportion(game_env):
    m = game_env.module
    m.region.temperature = 14.0
    m.region.capacity["preserve"] = 2  # 0.16
    m.region.capacity["monitor"] = 2   # 0.08
    b = m.rate_breakdown(m.region)
    assert math.isclose(b["preserve"], 2 * b["monitor"])


def test_breakdown_includes_policy_stance_and_rescue(game_env):
    m = game_env.module
    m.region.choose_policy_stance("mitigation")
    m.region.temperature = 14.0
    m.region.melt_started_round = 1
    assert m.rate_breakdown(m.region)["stance"] > 0
    m.region.rescue_rounds_left = 3
    b = m.rate_breakdown(m.region)
    assert b["rescue"] > 0
    assert math.isclose(b["total"], m.region.current_rise_rate())


def test_breakdown_before_melt_is_just_the_background(game_env):
    m = game_env.module
    b = m.rate_breakdown(m.region)
    assert b["raw_feedback"] == 0 and math.isclose(b["total"], m.base_rise_per_round())
    labels = [row[0] for row in m.rate_breakdown_rows(b)]
    assert labels[0].startswith("Background") and "takes off" not in " ".join(labels)


def test_breakdown_respects_long_game_scaling(game_env):
    m = game_env.module
    m.long_game = True
    m.region.temperature = 14.0
    assert math.isclose(m.rate_breakdown(m.region)["total"], m.region.current_rise_rate())


def test_inspector_renders_for_the_selected_region(game_env):
    m = game_env.module
    m.region_c.temperature = 13.0
    _select(game_env, "rate-inspector-region", "c")
    body = game_env.elements["rate-inspector-body"].innerHTML
    assert "Region C" in body and "rate-breakdown-svg" in body and "Warming rate this round" in body
    _select(game_env, "rate-inspector-region", "a")
    assert "Region A" in game_env.elements["rate-inspector-body"].innerHTML


def test_inspector_is_read_only(game_env):
    m = game_env.module
    before = (m.region.temperature, m.region.funds)
    m.render()
    assert (m.region.temperature, m.region.funds) == before


# --------------------------------------------------------------------------- G-10 accessibility
def test_graphs_carry_a_summary_sentence(game_env):
    m = game_env.module
    svg = m.mini_temp_graph_svg([1.0, 5.0, 11.0], "Region B")
    assert 'role="img"' in svg and "Region B temperature over 3 rounds" in svg
    assert "crossed the +10 degree melt threshold" in svg
    assert 'role="img"' not in m.mini_temp_graph_svg([1.0, 2.0])


def test_every_region_graph_is_labelled_after_a_round(game_env):
    game_env.toggle_worst_case_region()
    game_env.advance_round()
    game_env.advance_round()
    for element_id, name in (("graph", "Region A"), ("b-graph", "Region B"),
                             ("c-graph", "Region C"), ("d-graph", "Region D")):
        assert f"{name} temperature over" in game_env.elements[element_id].innerHTML


def test_round_summary_is_announced(game_env):
    game_env.advance_round()
    text = game_env.elements["sr-announcer"].innerText
    assert text.startswith("Round 2.") and "Region A +1.0 degrees, stable." in text


def test_announcer_names_tipping_and_critical_events(game_env):
    m = game_env.module
    m.region.temperature = 9.5
    game_env.advance_round()
    assert "Region A started melting." in game_env.elements["sr-announcer"].innerText
    m.region.temperature = 15.0
    game_env.advance_round()
    assert "Region A went critical." in game_env.elements["sr-announcer"].innerText


def test_announcer_mentions_balance_bonus(game_env):
    m = game_env.module
    for r in (m.region, m.region_b, m.region_c):
        _melting(r, 12.0)
    game_env.advance_round()
    assert "Perfect balance bonus earned." in game_env.elements["sr-announcer"].innerText
