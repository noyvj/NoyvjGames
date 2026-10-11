"""Round-8 pass: the sandbox balance panel (C-27)."""
import json

from .test_sandbox import dump, play_real_game


def _slide(env, key, value):
    el = env.elements[f"sandbox-bal-{key}"]
    el.value = str(value)

    class _Event:
        pass

    event = _Event()
    event.target = el
    el.dispatch("input", event)


def test_panel_is_hidden_outside_the_sandbox_and_shown_inside(game_env):
    g = game_env.module
    g.render()
    assert game_env.elements["sandbox-balance"].hidden is True
    g.sandbox_enter()
    assert game_env.elements["sandbox-balance"].hidden is False
    assert "All sliders at their usual values" in game_env.elements["sandbox-bal-note"].innerText
    g.sandbox_leave()
    assert game_env.elements["sandbox-balance"].hidden is True


def test_sliders_start_at_the_usual_numbers(game_env):
    g = game_env.module
    g.sandbox_enter()
    assert g.state.balance == g.SANDBOX_BALANCE_DEFAULTS
    assert g.state.demand_growth_this_round() == g.DEMAND_GROWTH_PER_ROUND
    assert g.state.revenue_per_unit == g.REVENUE_PER_UNIT_MET
    assert game_env.elements["sandbox-bal-growth-out"].innerText == "10"


def test_demand_growth_slider_changes_the_next_round(game_env):
    g = game_env.module
    g.sandbox_enter()
    _slide(game_env, "growth", 25)
    start = g.state.demand
    game_env.advance_round()
    assert g.state.demand == start + 25
    _slide(game_env, "growth", 0)
    held = g.state.demand
    game_env.advance_round()
    assert g.state.demand == held  # no floor of 3 when the slider is at 0
    assert "+0" in g.demand_growth_title()


def test_revenue_slider_changes_what_a_round_earns(game_env):
    g = game_env.module
    g.sandbox_enter()
    for _ in range(6):
        game_env.build("coal")
    base = g.state.funds
    game_env.advance_round()
    gain_normal = g.state.funds - base
    _slide(game_env, "revenue", 4)
    base = g.state.funds
    game_env.advance_round()
    gain_double = g.state.funds - base
    assert gain_double > gain_normal * 1.5
    assert g.state.last_round_recap is not None


def test_cost_slider_changes_how_fast_renewables_get_cheaper(game_env):
    g = game_env.module
    g.sandbox_enter()
    for _ in range(5):
        game_env.build("solar")
    cheap = g.state.plant_cost("solar")
    _slide(game_env, "cost-decay", 1.0)
    flat = g.state.plant_cost("solar")
    assert flat > cheap and flat == g.PLANT_BASE_COST["solar"] * 0.85  # the site-lease project is on too
    _slide(game_env, "cost-decay", 0.85)
    assert g.state.plant_cost("solar") < cheap
    # The usual value goes back to the normal rule (the R&D grant is on in the sandbox).
    _slide(game_env, "cost-decay", g.RD_GRANT_DECAY)
    assert g.state.cost_decay_override is None and g.state.plant_cost("solar") == cheap


def test_no_decay_setting_can_make_a_retire_refund_beat_the_build_price(game_env):
    g = game_env.module
    g.sandbox_enter()
    for decay in (0.85, 0.9, 0.95, 1.0):
        _slide(game_env, "cost-decay", decay)
        for plant in ("solar", "wind", "hydro", "coal", "battery"):
            for _ in range(30):
                g.state.cumulative_built[plant] += 1
                refund = g.state._learning_curve_cost(plant) * g.REFUND_FRACTION
                assert refund <= g.state.plant_cost(plant) + 1e-9


def test_breakdown_slider_turns_aging_breakdowns_on_in_proportion(game_env):
    g = game_env.module
    g.sandbox_enter()
    g.state.plant_counts["coal"] = 3
    g.state.plant_age["coal"] = 20.0
    assert g.state.aging_breakdown_probability() == 0.0 and g.state.breakdown_risk_probability("coal") == 0.0
    _slide(game_env, "breakdown", 100)
    real = g.GridState.aging_breakdown_probability(g.state)
    assert real > 0 and abs(g.state.aging_breakdown_probability() - real) < 1e-9
    _slide(game_env, "breakdown", 300)
    assert g.state.aging_breakdown_probability() == min(g.MAX_AGE_BREAKDOWN_PROBABILITY, real * 3)
    _slide(game_env, "breakdown", 0)
    assert g.state.aging_breakdown_probability() == 0.0


def test_values_are_clamped_and_junk_is_refused(game_env):
    g = game_env.module
    g.sandbox_enter()
    assert g.state.set_balance("growth", 999) == 30.0
    assert g.state.set_balance("growth", -5) == 0.0
    assert g.state.set_balance("revenue", "abc") is None
    assert g.state.set_balance("revenue", float("nan")) is None
    assert g.state.set_balance("nothing", 1) is None
    assert g.state.balance["revenue"] == g.REVENUE_PER_UNIT_MET


def test_reset_button_restores_the_usual_numbers(game_env):
    g = game_env.module
    g.sandbox_enter()
    _slide(game_env, "growth", 3)
    _slide(game_env, "revenue", 5)
    _slide(game_env, "cost-decay", 1.0)
    assert "Changed:" in game_env.elements["sandbox-bal-note"].innerText
    game_env.elements["sandbox-bal-reset"].dispatch("click", None)
    assert g.state.balance == g.SANDBOX_BALANCE_DEFAULTS
    assert g.state.cost_decay_override is None and g.state.revenue_per_unit == 2 and g.state.base_demand_growth == 10


def test_changing_scenario_in_the_sandbox_keeps_the_sliders(game_env):
    g = game_env.module
    g.sandbox_enter()
    _slide(game_env, "growth", 4)
    game_env.elements["scenario-toggle-button"].dispatch("click", None)
    assert g.state.balance["growth"] == 4 and g.state.base_demand_growth == 4


def test_sliders_do_nothing_outside_the_sandbox(game_env):
    g = game_env.module
    _slide(game_env, "growth", 30)
    assert g.state.base_demand_growth == g.DEMAND_GROWTH_PER_ROUND
    assert g.state.demand_growth_this_round() == g.DEMAND_GROWTH_PER_ROUND


def test_sandbox_balance_never_reaches_the_real_game_career_or_saves(game_env):
    g = play_real_game(game_env)
    before = dump(g.get_state())
    career_points = g.career["points"]
    g.sandbox_enter()
    _slide(game_env, "growth", 30)
    _slide(game_env, "revenue", 6)
    _slide(game_env, "cost-decay", 0.85)
    _slide(game_env, "breakdown", 300)
    for _ in range(8):
        game_env.advance_round()
    assert g.finish_run() is None or g.career["points"] == career_points
    assert g.career["points"] == career_points
    assert g.achievement_ids_earned() == g._sandbox_real["earned"]
    assert dump(g.get_state()) == before
    assert "balance" not in json.dumps(g.get_state())
    g.sandbox_leave()
    assert dump(g.get_state()) == before
    assert g.state.base_demand_growth == 10 and g.state.revenue_per_unit == 2 and g.state.cost_decay_override is None


def test_a_real_run_ignores_the_new_hooks(game_env):
    g = game_env.module
    assert g.GridState.revenue_per_unit == g.REVENUE_PER_UNIT_MET
    assert g.GridState.base_demand_growth == g.DEMAND_GROWTH_PER_ROUND
    assert g.GridState.cost_decay_override is None
    assert g.state.demand_growth_this_round() == g.DEMAND_GROWTH_PER_ROUND
    assert g.SandboxGridState().sandbox is True
