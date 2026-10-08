"""Round-3 batch 2 (2026-10-08): Perfect Fit streak (GI-13), Crisis Calendar and
Surge Tests (GI-2, GI-11), Mayor's Council (GI-1), Budget Autopilot (GI-5),
star ratings (GI-21) and the copy-able run summary (I-18)."""

import json
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _build_to_cover(env, margin=3.0):
    """Buy housing until capacity just covers everyone who has arrived."""
    region = env.region
    while region.total_capacity() < region.total_arrivals + margin and region.funds >= 20:
        region.invest("housing")


def _advance(env, n=1):
    for _ in range(n):
        env.advance_round()


# ---- GI-13: Perfect Fit ------------------------------------------------------
def test_perfect_fit_needs_capacity_and_arrivals(game_env):
    region = game_env.region
    assert region.is_perfect_fit() is False  # nothing built, nobody arrived
    region.total_arrivals = 40.0
    region.capacity["housing"] = 45.0
    assert region.is_perfect_fit() is True
    region.capacity["housing"] = 39.0
    assert region.is_perfect_fit() is False  # short
    region.capacity["housing"] = 60.0
    assert region.is_perfect_fit() is False  # overbuilt beyond the margin


def test_perfect_fit_streak_grows_pays_and_resets(game_env):
    region = game_env.region
    region.total_arrivals = 40.0
    region.capacity["housing"] = 42.0
    funds_before = region.funds
    _advance(game_env)
    assert region.perfect_fit_streak == 1
    plain_income = 50.0 * (1 - 0.0)  # no strain, nobody integrated
    assert region.funds - funds_before == plain_income + 3.0
    region.capacity["housing"] = region.total_arrivals + 2
    _advance(game_env)
    assert region.perfect_fit_streak == 2
    assert region.best_perfect_fit_streak == 2
    region.capacity["housing"] = 0.0
    _advance(game_env)
    assert region.perfect_fit_streak == 0
    assert region.best_perfect_fit_streak == 2


def test_perfect_fit_bonus_is_capped(game_env):
    region = game_env.region
    for _ in range(8):
        region.capacity["housing"] = region.total_arrivals + 1 if region.total_arrivals > 0 else 5.0
        region.total_arrivals = max(region.total_arrivals, 4.0)
        region.capacity["housing"] = region.total_arrivals + 1
        before = region.funds
        _advance(game_env)
    assert region.perfect_fit_streak == 8
    # the last round paid the capped bonus (5 rounds x 3), not 8 x 3
    assert region.funds - before <= 50.0 + 15.0 + region.integration_contribution() + 1e-6


def test_perfect_fit_message_states_the_rule_and_the_streak(game_env):
    text = game_env.module.perfect_fit_message()
    assert "Perfect Fit" in text and "12" in text
    region = game_env.region
    region.total_arrivals = 40.0
    region.capacity["housing"] = 42.0
    _advance(game_env)
    assert "streak: 1" in game_env.module.perfect_fit_message()
    assert game_env.elements["perfect-fit-display"].innerText.startswith("Perfect Fit")


def test_perfect_fit_round_trips_in_a_save(game_env):
    region = game_env.region
    region.perfect_fit_streak = 3
    region.best_perfect_fit_streak = 5
    state = game_env.module.get_state()
    assert state["perfect_fit"] == {"streak": 3, "best": 5}
    region.perfect_fit_streak = 0
    region.best_perfect_fit_streak = 0
    game_env.module.load_state(json.loads(json.dumps(state)))
    assert (region.perfect_fit_streak, region.best_perfect_fit_streak) == (3, 5)
    game_env.module.load_state({"perfect_fit": {"streak": 9, "best": 2}})
    assert region.perfect_fit_streak == 2  # streak can never exceed the best
    game_env.module.load_state({"perfect_fit": "junk"})
    assert region.best_perfect_fit_streak == 0


def test_a_fresh_save_has_no_new_keys(game_env):
    state = game_env.module.get_state()
    for key in ("perfect_fit", "calendar", "council", "autopilot", "stars_banked"):
        assert key not in state


# ---- GI-2 / GI-11: Crisis Calendar -------------------------------------------
def test_calendar_schedule_matches_the_documented_rule(game_env):
    f = game_env.module.calendar_event_for_round
    assert f(7) is None
    assert f(8)["kind"] == "bumper_harvest"
    assert f(12)["kind"] == "surge"
    assert f(16)["kind"] == "budget_cut"
    assert f(20)["kind"] == "flood"
    assert f(24)["kind"] == "bumper_harvest"
    assert f(25)["kind"] == "boss" and f(25)["name"] == "The Long Queue"
    assert f(50)["kind"] == "boss" and f(75)["kind"] == "boss"
    assert f(100)["kind"] == "flood"
    assert f(101) is None
    assert f(13) is None
    # deterministic: asking twice gives the same answer
    assert f(36) == f(36)


def test_calendar_is_off_by_default_and_changes_nothing(game_env):
    region = game_env.region
    assert region.calendar_enabled is False
    assert region.calendar_event(12) is None
    region.round_number = 12
    assert region.arrivals_this_round() == 5.0 + region.background_severity * 3.0


def test_toggle_calendar_button(game_env):
    el = game_env.elements["calendar-toggle-button"]
    assert el.innerText == "Crisis Calendar: OFF"
    el.dispatch("click", None)
    assert game_env.region.calendar_enabled is True
    assert el.innerText == "Crisis Calendar: ON"
    assert game_env.elements["calendar-brace-button"].hidden is False
    el.dispatch("click", None)
    assert game_env.region.calendar_enabled is False
    assert game_env.elements["calendar-brace-button"].hidden is True


def test_preview_shows_this_round_and_next_round(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 11
    text = game_env.module.calendar_message()
    assert "Next round (round 12)" in text and "surge" in text.lower()
    region.round_number = 12
    assert "This round (round 12)" in game_env.module.calendar_message()
    region.round_number = 13
    assert "Next event: round 16" in game_env.module.calendar_message()


def test_surge_raises_arrivals_and_bracing_softens_it(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 12
    region.background_severity = 4.0
    base = 5.0 + 4.0 * 3.0
    assert abs(region.arrivals_this_round() - base * 1.4) < 1e-9
    region.funds = 100.0
    assert region.brace() is True
    assert region.funds == 75.0
    assert abs(region.arrivals_this_round() - base * 1.2) < 1e-9
    assert region.brace() is False  # already braced, nothing else to brace for this round


def test_brace_can_be_bought_a_round_early(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 11
    region.funds = 100.0
    target = region.brace_target()
    assert target["round"] == 12
    assert region.brace() is True
    assert 12 in region.braced_rounds


def test_brace_needs_funds_and_a_braceable_event(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 12
    region.funds = 10.0
    assert region.brace() is False
    region.round_number = 8  # bumper harvest: nothing to brace
    region.funds = 500.0
    assert region.brace_target() is None
    assert region.brace() is False


def test_budget_cut_and_bumper_harvest_change_income(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 8
    funds = region.funds
    region.advance_round()
    assert region.funds - funds == 50.0 + 40.0  # bumper harvest
    region.round_number = 16
    funds = region.funds
    region.strain_log.clear()
    region.advance_round()
    assert abs((region.funds - funds) - 50.0 * (1 - region.strain_log[-1]) * 0.7) < 1e-6
    region.round_number = 16
    region.braced_rounds = [16]
    funds = region.funds
    region.advance_round()
    assert abs((region.funds - funds) - 50.0 * (1 - region.strain_log[-1]) * 0.9) < 1e-6


def test_flood_damages_infrastructure_and_bracing_limits_it(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.capacity["infrastructure"] = 30.0
    region.round_number = 20
    region.advance_round()
    assert region.capacity["infrastructure"] == 18.0
    region.round_number = 20
    region.braced_rounds = [20]
    region.advance_round()
    assert region.capacity["infrastructure"] == 14.0
    region.capacity["infrastructure"] = 2.0
    region.round_number = 20
    region.braced_rounds = []
    region.advance_round()
    assert region.capacity["infrastructure"] == 0.0  # never negative


def test_surge_test_held_the_line_card(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 25
    region.background_severity = 10.0
    region.capacity["housing"] = 5000.0
    region.advance_round()
    entry = region.calendar_log[-1]
    assert entry["kind"] == "boss" and entry["held"] is True
    assert "Held the line" in game_env.module.calendar_result_message(entry)
    game_env.module.render()
    assert "Held the line" in game_env.elements["calendar-note"].innerText


def test_surge_test_that_outruns_capacity_is_gentle(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 50
    region.background_severity = 25.0
    region.advance_round()
    entry = region.calendar_log[-1]
    assert entry["held"] is False
    message = game_env.module.calendar_result_message(entry)
    assert "recovers" in message and "Held the line" not in message


def test_boss_arrivals_scale_with_the_severity_curve(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 25
    region.background_severity = 12.5
    base = 5.0 + 12.5 * 3.0
    assert abs(region.arrivals_this_round() - base * 1.8) < 1e-9
    region.braced_rounds = [25]
    assert abs(region.arrivals_this_round() - base * 1.5) < 1e-9


def test_play_rounds_refuses_to_run_through_an_unbraced_event(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 12
    advanced, reason = game_env.module.play_rounds()
    assert advanced == 0 and "Arrivals surge" in reason and "brace" in reason
    region.braced_rounds = [12]
    advanced, reason = game_env.module.play_rounds(1)
    assert advanced == 1


def test_play_rounds_stops_when_a_braceable_event_is_next(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 9
    region.capacity["housing"] = 5000.0  # keep strain flat so only the calendar can stop it
    advanced, reason = game_env.module.play_rounds()
    assert region.round_number == 11
    assert advanced == 2 and "next round" in reason


def test_play_rounds_unchanged_with_calendar_off(game_env):
    region = game_env.region
    region.round_number = 9
    region.capacity["housing"] = 5000.0
    advanced, reason = game_env.module.play_rounds()
    assert advanced == 5 and reason is None


def test_reset_round_refunds_a_brace(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 12
    region.funds = 100.0
    game_env.module.round_start_snapshot = game_env.module._take_round_start_snapshot()
    game_env.elements["calendar-brace-button"].dispatch("click", None)
    assert region.funds == 75.0 and 12 in region.braced_rounds
    assert game_env.module.reset_round() is True
    assert region.funds == 100.0 and region.braced_rounds == []


def test_calendar_state_round_trips(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.round_number = 12
    region.funds = 100.0
    region.brace()
    region.advance_round()
    state = json.loads(json.dumps(game_env.module.get_state()))
    assert state["calendar"]["enabled"] is True and state["calendar"]["braced"] == [12]
    region.calendar_enabled = False
    region.braced_rounds = []
    region.calendar_log = []
    game_env.module.load_state(state)
    assert region.calendar_enabled is True
    assert region.braced_rounds == [12]
    assert region.calendar_log[-1]["kind"] == "surge" and region.calendar_log[-1]["braced"] is True


def test_calendar_load_rejects_bad_data(game_env):
    bad = {"calendar": {"enabled": "yes", "braced": [12, "x", -3, 13, True], "log": [{"round": "x"}, 5, {"round": 12, "kind": "nope", "braced": True, "held": None}]}}
    game_env.module.load_state(bad)
    region = game_env.region
    assert region.calendar_enabled is False
    assert region.braced_rounds == [12]  # 13 has no event, the rest are not rounds
    assert region.calendar_log == []


def test_rewind_restores_the_calendar_effects(game_env):
    region = game_env.region
    region.calendar_enabled = True
    region.capacity["infrastructure"] = 30.0
    region.round_number = 20
    game_env.advance_round()
    assert region.capacity["infrastructure"] == 18.0
    game_env.elements["rewind-button"].dispatch("click", None)
    game_env.elements["rewind-button"].dispatch("click", None)
    assert game_env.region.capacity["infrastructure"] == 30.0
    assert game_env.region.calendar_log == []


# ---- GI-1: Mayor's Council ---------------------------------------------------
def test_council_lists_nine_programs_each_with_a_tradeoff(game_env):
    programs = game_env.module.COUNCIL_PROGRAMS
    assert len(programs) == 9
    names = {p["name"] for p in programs}
    assert {"Night-School Network", "Rapid Housing Modules", "Transit Expansion"} <= names
    for p in programs:
        assert p["effect"] and p["tradeoff"], p["id"]
        assert set(p["effect"]).isdisjoint(p["tradeoff"]) or p["effect"] != p["tradeoff"]
    branches = {p["branch"] for p in programs}
    assert branches == {"education", "housing", "transit"}
    for branch in branches:
        assert sorted(p["tier"] for p in programs if p["branch"] == branch) == [1, 2, 3]


def test_council_pick_opens_every_ten_completed_rounds(game_env):
    m = game_env.module
    region = game_env.region
    region.round_number = 10  # nine rounds completed
    assert m.council_pending_picks() == 0
    region.round_number = 11
    assert m.council_pending_picks() == 1
    assert m.council_pick("education") is True
    assert m.council_pending_picks() == 0
    assert m.council_pick("housing") is False  # no pick waiting
    region.round_number = 31
    assert m.council_pending_picks() == 2


def test_council_picks_walk_a_branch_tier_by_tier(game_env):
    m = game_env.module
    region = game_env.region
    region.round_number = 91
    for expected in ("night_school", "language_cafes", "credential_bridge"):
        assert m.council_pick("education") is True
        assert region.council_picks[-1] == expected
    assert m.council_pick("education") is False  # branch complete
    assert m.council_options().get("education") is None
    assert set(m.council_options()) == {"housing", "transit"}


def test_council_effects_apply(game_env):
    region = game_env.region
    base_coverage = region.coverage_bonus()
    region.council_picks = ["rapid_housing"]
    assert region.coverage_bonus() == base_coverage + 12.0
    assert region.program_effect("income") == -3.0  # its trade-off
    region.council_picks = ["night_school"]
    region.capacity["services"] = 100.0
    region.total_arrivals = 1000.0
    region.integrated_population = 0.0
    assert abs(region.integration_this_round() - 100.0 * 0.3 * 1.15) < 1e-9
    region.advance_round()  # runs cleanly with the program in place


def test_council_income_tradeoff_changes_funds(game_env):
    region = game_env.region
    funds = region.funds
    region.advance_round()
    plain = region.funds - funds
    region2_funds = region.funds
    region.round_number = 1
    region.council_picks = ["regional_hub"]  # +8 income, -10 coverage
    region.total_arrivals = 0.0
    region.strain_log.clear()
    region.advance_round()
    assert abs((region.funds - region2_funds) - (plain + 8.0)) < 1e-6


def test_council_coverage_penalty_cannot_push_strain_above_one(game_env):
    region = game_env.region
    region.council_picks = ["regional_hub"]
    region.total_arrivals = 50.0
    assert 0.0 <= region.strain_fraction() <= 1.0


def test_council_buttons_and_tree_render(game_env):
    region = game_env.region
    region.round_number = 11
    game_env.module.render()
    assert game_env.elements["council-pick-education"].disabled is False
    assert game_env.elements["council-pick-education"].innerText == "Learning: Night-School Network"
    game_env.elements["council-pick-transit"].dispatch("click", None)
    assert region.council_picks == ["transit_expansion"]
    assert game_env.elements["council-pick-housing"].disabled is True  # no pick left until round 21
    assert "Adopted: Transit Expansion" in game_env.elements["council-status"].innerText
    tree = game_env.elements["council-tree"].innerHTML
    assert "✓ <strong>Transit Expansion" in tree and "○ <strong>Commuter Corridors" in tree
    assert tree.count("<strong>") >= 9


def test_council_save_round_trip_and_tier_skip_rejected(game_env):
    region = game_env.region
    region.council_picks = ["rapid_housing", "modular_retrofit"]
    state = json.loads(json.dumps(game_env.module.get_state()))
    assert state["council"] == ["rapid_housing", "modular_retrofit"]
    region.council_picks = []
    game_env.module.load_state(state)
    assert region.council_picks == ["rapid_housing", "modular_retrofit"]
    game_env.module.load_state({"council": ["pattern_book", "night_school", "night_school", 5, "nope"]})
    assert region.council_picks == ["night_school"]  # tier 3 before tier 1 is rejected, duplicates too


def test_council_never_forces_a_choice(game_env):
    region = game_env.region
    for _ in range(25):
        region.advance_round()
    assert region.council_picks == []


# ---- GI-5: Budget Autopilot --------------------------------------------------
def test_autopilot_defaults_and_clean_rules(game_env):
    m = game_env.module
    assert game_env.region.autopilot == {"services_share": 0.5, "surplus": "housing", "reserve": 40, "rounds": 10}
    assert m._clean_autopilot(None) == m.AUTOPILOT_DEFAULT_RULES
    cleaned = m._clean_autopilot({"services_share": None, "surplus": "nonsense", "reserve": 5, "rounds": 25})
    assert cleaned == {"services_share": None, "surplus": "housing", "reserve": 40, "rounds": 25}
    assert m._clean_autopilot({"reserve": True})["reserve"] == 40


def test_autopilot_run_buys_by_the_rules_and_advances(game_env):
    m = game_env.module
    region = game_env.region
    region.autopilot = {"services_share": 0.5, "surplus": "housing", "reserve": 40, "rounds": 5}
    advanced, reason = m.autopilot_run()
    assert advanced == 5 and reason is None
    assert region.round_number == 6
    assert region.total_capacity() > 0
    assert region.capacity["services"] > 0 and region.capacity["housing"] > 0
    assert all(row["auto"] for row in region.ledger)
    assert any("bought" in line for line in m.autopilot_log)
    assert m.autopilot_log[-1].startswith("Stopped after 5 rounds")


def test_autopilot_keeps_the_reserve(game_env):
    m = game_env.module
    region = game_env.region
    region.autopilot = {"services_share": None, "surplus": "housing", "reserve": 100, "rounds": 5}
    region.funds = 130.0
    m._autopilot_buy_round()
    assert region.funds >= 100.0
    region.autopilot = {"services_share": None, "surplus": None, "reserve": 0, "rounds": 5}
    before = dict(region.capacity)
    m._autopilot_buy_round()
    assert region.capacity == before  # hold means hold
    assert "nothing to buy" in m.autopilot_log[-1]


def test_autopilot_services_share_rule(game_env):
    m = game_env.module
    region = game_env.region
    region.autopilot = {"services_share": 0.6, "surplus": None, "reserve": 0, "rounds": 5}
    region.funds = 500.0
    m._autopilot_buy_round()
    total = region.total_capacity()
    assert region.capacity["services"] / total >= 0.6
    assert region.capacity["housing"] == 0.0


def test_autopilot_stops_when_strain_rises(game_env):
    m = game_env.module
    region = game_env.region
    region.autopilot = {"services_share": None, "surplus": None, "reserve": 0, "rounds": 25}
    region.capacity["housing"] = 40.0
    advanced, reason = m.autopilot_run()
    assert advanced < 25 and "strain rose" in reason


def test_autopilot_run_via_buttons_and_selects(game_env):
    el = game_env.elements
    el["autopilot-share-select"].value = "60"
    el["autopilot-surplus-select"].value = "services"
    el["autopilot-reserve-select"].value = "100"
    el["autopilot-rounds-select"].value = "5"
    el["autopilot-rounds-select"].dispatch("change", None)
    assert game_env.region.autopilot == {"services_share": 0.6, "surplus": "services", "reserve": 100, "rounds": 5}
    assert el["autopilot-run-button"].innerText == "▶ Run Autopilot (5 rounds)"
    el["autopilot-run-button"].dispatch("click", None)
    assert game_env.region.round_number > 1
    assert "Autopilot ran" in el["round-tools-note"].innerText
    assert el["autopilot-log"].innerHTML.count("<li>") >= 2


def test_autopilot_off_value_and_hold(game_env):
    el = game_env.elements
    el["autopilot-share-select"].value = "off"
    el["autopilot-surplus-select"].value = "hold"
    el["autopilot-share-select"].dispatch("change", None)
    assert game_env.region.autopilot["services_share"] is None
    assert game_env.region.autopilot["surplus"] is None
    assert "no services-share rule" in el["autopilot-note"].innerText


def test_autopilot_rules_save_and_load(game_env):
    region = game_env.region
    region.autopilot = {"services_share": None, "surplus": "infrastructure", "reserve": 100, "rounds": 25}
    state = json.loads(json.dumps(game_env.module.get_state()))
    assert state["autopilot"]["surplus"] == "infrastructure"
    region.autopilot = dict(game_env.module.AUTOPILOT_DEFAULT_RULES)
    game_env.module.load_state(state)
    assert region.autopilot == {"services_share": None, "surplus": "infrastructure", "reserve": 100, "rounds": 25}
    game_env.module.load_state({"autopilot": [1, 2]})
    assert region.autopilot == game_env.module.AUTOPILOT_DEFAULT_RULES
    assert game_env.module.autopilot_log == []


def test_autopilot_rounds_can_be_rewound_one_at_a_time(game_env):
    m = game_env.module
    game_env.region.autopilot = {"services_share": 0.5, "surplus": "housing", "reserve": 0, "rounds": 5}
    m.autopilot_run()
    assert m.rewind_available()
    assert game_env.region.round_number == 6


def test_autopilot_does_not_block_achievements(game_env):
    m = game_env.module
    game_env.region.autopilot = {"services_share": 0.5, "surplus": "housing", "reserve": 0, "rounds": 10}
    m.autopilot_run()
    assert "first_investment" in m.achievement_ids_earned()


# ---- GI-21: stars ------------------------------------------------------------
def test_star_goals_follow_the_thresholds(game_env):
    m = game_env.module
    region = game_env.region
    assert m.star_goals() == {"wellbeing": 0, "speed": 0, "efficiency": 0}
    region.net_positive_round = 6
    assert m.star_goals()["speed"] == 3
    region.net_positive_round = 9
    assert m.star_goals()["speed"] == 2
    region.net_positive_round = 16
    assert m.star_goals()["speed"] == 1
    region.net_positive_round = 17
    assert m.star_goals()["speed"] == 0
    region.capacity["housing"] = 10.0  # invested 20
    region.cumulative_integration_contribution = 20.0 * 4.0
    assert m.star_goals()["efficiency"] == 2
    region.cumulative_integration_contribution = 20.0 * 9.0
    assert m.star_goals()["efficiency"] == 3
    region.funds = 1000.0
    region.strain_log = [0.0]
    region._strain_sum, region._strain_count = 0.0, 1
    region.integrated_population = region.total_arrivals = 1.0
    assert m.star_goals()["wellbeing"] >= 1


def test_stars_text_and_live_line(game_env):
    m = game_env.module
    assert m.stars_text(2) == "★★☆"
    game_env.module.render()
    text = game_env.elements["run-stars-display"].innerText
    assert "Run stars so far" in text and "round 50" in text


def test_stars_bank_once_at_the_end_of_round_fifty(game_env):
    m = game_env.module
    region = game_env.region
    m.run_history.clear()
    region.round_number = 49
    game_env.advance_round()
    assert region.stars_banked is None and m.run_history == []
    game_env.advance_round()  # completes round 50
    assert region.stars_banked == 50
    assert len(m.run_history) == 1
    entry = m.run_history[0]
    assert len(entry["stars"]) == 3 and all(0 <= n <= 3 for n in entry["stars"])
    game_env.advance_round()
    assert len(m.run_history) == 1
    assert "Banked into your run history at round 50" in m.run_stars_message()


def test_rewinding_across_the_bank_does_not_double_count(game_env):
    m = game_env.module
    region = game_env.region
    m.run_history.clear()
    region.round_number = 50
    game_env.advance_round()
    assert len(m.run_history) == 1
    game_env.elements["rewind-button"].dispatch("click", None)
    game_env.elements["rewind-button"].dispatch("click", None)
    assert game_env.region.stars_banked is None
    game_env.advance_round()
    assert len(m.run_history) == 1


def test_run_history_is_capped_and_listed_best_first(game_env):
    m = game_env.module
    m.run_history.clear()
    for index in range(m.RUN_HISTORY_MAX + 4):
        m.run_history.append({"name": f"R{index}", "round": 50, "stars": [index % 4, 1, 1], "token": f"t{index}"})
    html = m.run_history_html()
    assert html.count("<li>") == 5
    first = html.split("<li>")[1]
    assert "★★★" in first  # a three-star wellbeing entry sorts first
    assert m._clean_run_history([{"stars": [1, 2, 9], "token": "x"}, "junk", {"stars": [1, 2, 3], "token": "ok", "name": "A"}]) == [
        {"name": "A", "round": 50, "stars": [1, 2, 3], "token": "ok"}
    ]


def test_collection_panel_shows_run_history(game_env):
    game_env.elements["collection-toggle-button"].dispatch("click", None)
    assert "No banked runs yet" in game_env.elements["collection-list"].innerHTML


def test_stars_banked_marker_saves(game_env):
    region = game_env.region
    region.stars_banked = 50
    state = json.loads(json.dumps(game_env.module.get_state()))
    assert state["stars_banked"] == 50
    region.stars_banked = None
    game_env.module.load_state(state)
    assert region.stars_banked == 50
    game_env.module.load_state({"stars_banked": -4})
    assert region.stars_banked is None


# ---- I-18: copy run summary --------------------------------------------------
def test_wellbeing_curve_blocks(game_env):
    m = game_env.module
    assert m.wellbeing_curve([]) == ""
    assert m.wellbeing_curve([0, 50, 100]) == "▁▅█"
    long = m.wellbeing_curve(list(range(0, 100)), width=30)
    assert len(long) == 30 and long[0] == "▁" and long[-1] == "█"


def test_band_names(game_env):
    m = game_env.module
    assert [m.wellbeing_band(s) for s in (10, 40, 70, 90)] == ["Struggling", "Managing", "Thriving", "Model Region"]


def test_run_summary_text(game_env):
    m = game_env.module
    region = game_env.region
    region.region_name = "Lakeside"
    region.calendar_enabled = True
    region.council_picks = ["night_school"]
    for _ in range(3):
        game_env.advance_round()
    text = m.run_summary_text()
    lines = text.split("\n")
    assert lines[0] == "Drift: Lakeside"
    assert lines[1].startswith("After 3 rounds:")
    assert lines[2].startswith("Wellbeing curve: ") and len(lines[2]) > len("Wellbeing curve: ")
    assert "Crisis Calendar" in lines[3] and "Night-School Network" in lines[3]
    assert lines[4].startswith("Stars:")


def test_copy_summary_falls_back_to_a_text_box(game_env):
    el = game_env.elements
    el["copy-summary-button"].dispatch("click", None)
    assert el["summary-copy-area"].hidden is False
    assert el["summary-copy-area"].value.startswith("Drift: Unnamed region")
    assert "Could not copy" in el["round-tools-note"].innerText


# ---- pages -------------------------------------------------------------------
NEW_IDS = [
    "perfect-fit-display", "calendar-toggle-button", "calendar-display", "calendar-brace-button", "calendar-note",
    "council-status", "council-pick-education", "council-pick-housing", "council-pick-transit", "council-tree",
    "autopilot-share-select", "autopilot-surplus-select", "autopilot-reserve-select", "autopilot-rounds-select",
    "autopilot-run-button", "autopilot-note", "autopilot-log", "run-stars-display", "copy-summary-button",
    "summary-copy-area", "civic-tools",
]


def test_every_new_element_exists_in_both_pages():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        for element_id in NEW_IDS:
            assert f'id="{element_id}"' in html, f"{element_id} missing from {page}"


def test_civic_tools_sit_in_the_desktop_side_column():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert "#civic-tools" in config["zones"]["side"]


def test_changelog_mentions_the_new_features():
    entries = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    newest = entries[0]["entry"]
    for word in ("Perfect Fit", "Crisis Calendar", "Council", "Autopilot", "stars"):
        assert word in newest
