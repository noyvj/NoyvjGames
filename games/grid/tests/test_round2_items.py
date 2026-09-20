"""2026-09-20 Grid pass (planning/TODO.md C4/C5/C10/C11/C12/C13/C14/C15/
C18/C20/C22/C24/C25/C26/C28): small UI/mechanic additions."""

import sys

from .test_confirm_dialog import _install_fake_confirm_dialog


def test_c22_steeper_label_shows_multiplier(game_env):
    assert "x2" in game_env.elements["steeper-demand-toggle-button"].innerText
    game_env.toggle_steeper_demand()
    assert "x2" in game_env.elements["steeper-demand-toggle-button"].innerText


def test_c20_demand_arrow_reflects_growth(game_env):
    assert "▬" in game_env.elements["demand-display"].innerText
    game_env.toggle_steeper_demand()
    assert "▲" in game_env.elements["demand-display"].innerText
    assert "+20" in game_env.elements["demand-display"].title


def test_c28_streak_counter_visible(game_env):
    assert "0 round" in game_env.elements["streak-display"].innerText
    game_env.state.emissions = 0.0
    game_env.advance_round()
    assert "1 round" in game_env.elements["streak-display"].innerText


def test_c4_c26_wear_tooltip_and_tier_glyph(game_env):
    game_env.build("coal")
    game_env.state.plant_age["coal"] = 20.0
    game_env.module.render()
    el = game_env.elements["coal-wear-pct"]
    assert "◑" in el.innerText  # wear-2 tier
    assert "24 rounds" in el.title and "Maintain" in el.title
    game_env.state.plant_age["coal"] = 30.0
    game_env.module.render()
    assert "●" in el.innerText


def test_c18_retire_dialog_shows_wear(game_env):
    game_env.build("coal")
    game_env.state.plant_age["coal"] = 12.0
    fake_window = _install_fake_confirm_dialog()
    game_env.retire("coal")
    msg = fake_window.ConfirmDialog.calls[0]["message"]
    assert "wear 50%" in msg and "12.0 rounds" in msg


def test_c10_disruption_reason_names_plant(game_env):
    m = game_env.module
    damage = {"type": "damage", "severity": 0.6, "revenue_loss": 1, "damaged_plant": "coal", "cause_plant": "coal"}
    assert "Coal" in m.disruption_reason(damage) and "60%" in m.disruption_reason(damage)
    brown = {"type": "brownout", "severity": 0.2, "revenue_loss": 1, "cause_plant": "gas"}
    assert "Gas" in m.disruption_reason(brown)
    lingering = {"type": "brownout", "severity": 0.2, "revenue_loss": 1, "cause_plant": None}
    assert "historical" in m.disruption_reason(lingering)


def test_c10_toast_includes_reason(game_env):
    game_env.build("coal")
    game_env.state.emissions = 100000.0
    game_env.module.state.last_event = {"type": "brownout", "severity": 1.0, "revenue_loss": 5, "cause_plant": "coal"}
    game_env.module._check_disruption_toast()
    assert "Why:" in game_env.elements["disruption-toast-text"].innerText


def test_c5_grade_thresholds(game_env):
    s = game_env.state
    assert s.benchmark_grade() is None
    s.global_reference_emissions = 1000.0
    for emissions, letter in [(100, "A"), (400, "B"), (700, "C"), (950, "D"), (1200, "F")]:
        s.emissions = emissions
        assert s.benchmark_grade() == letter
    game_env.toggle_summary_panel()
    assert "Operator grade: F" in game_env.elements["summary-panel"].innerHTML


def test_c11_resilience_score(game_env):
    s = game_env.state
    assert s.resilience_score() == 0
    s.plant_counts["solar"] = 5
    assert s.resilience_score() == 0
    for t in ("coal", "gas", "nuclear", "solar", "wind", "hydro"):
        s.plant_counts[t] = 0
    # equal capacity share across all six types -> 100
    caps = game_env.module.PLANT_CAPACITY
    for t in ("coal", "gas", "nuclear", "solar", "wind", "hydro"):
        s.plant_counts[t] = 1200 // caps[t]
    assert s.resilience_score() == 100
    s.plant_counts["solar"] = 5
    for t in ("coal", "gas", "nuclear", "wind", "hydro"):
        s.plant_counts[t] = 0
    assert 0 <= s.resilience_score() < 100


def test_c25_projection(game_env):
    game_env.state.plant_counts["coal"] = 5
    p = game_env.state.projection()
    assert p["rounds"] == 20
    assert p["emissions"] == 5 * 20 * 3.0 * 20
    assert p["bau_emissions"] == p["emissions"]
    assert p["demand"] == 100 + 200
    game_env.toggle_summary_panel()
    assert "20 more rounds" in game_env.elements["summary-panel"].innerHTML


def test_c12_best_round_marker(game_env):
    m = game_env.module
    svg = m.trend_graph_svg([1, 2, 3], [5, 4, 3], [2, 3, 4], [0.1, 0.5, 0.3])
    assert "trend-best-marker" in svg and "Best round: Round 2" in svg
    assert "trend-best-marker" not in m.trend_graph_svg([1, 2, 3], [5, 4, 3], [2, 3, 4], [0, 0, 0])
    assert "trend-best-marker" not in m.trend_graph_svg([1, 2, 3], [5, 4, 3], [2, 3, 4])


def test_c13_scenarios(game_env):
    s = game_env.state
    btn = game_env.elements["scenario-toggle-button"]
    assert "Standard" in btn.innerText and not btn.disabled
    btn.dispatch("click", None)
    assert s.scenario == "coal_legacy" and s.plant_counts["coal"] == 4 and s.funds == 300
    btn.dispatch("click", None)
    assert s.scenario == "greenfield" and s.funds == 700 and s.plant_counts["coal"] == 0
    btn.dispatch("click", None)
    assert s.scenario == "standard" and s.funds == 500 and sum(s.plant_counts.values()) == 0
    game_env.build("coal")
    assert btn.disabled
    btn.dispatch("click", None)  # locked: no change
    assert s.scenario == "standard"


def test_c13_scenario_locked_after_round(game_env):
    game_env.advance_round()
    assert not game_env.state.apply_scenario("greenfield")
    assert game_env.elements["scenario-toggle-button"].disabled


def test_c13_scenario_persists_and_old_saves_default(game_env):
    game_env.state.apply_scenario("coal_legacy")
    saved = game_env.module.get_state()
    assert saved["scenario"] == "coal_legacy"
    del saved["scenario"]
    game_env.state.scenario = "greenfield"
    game_env.module.load_state(saved)
    assert game_env.state.scenario == "greenfield"  # missing key keeps live
    saved["scenario"] = "bogus"
    game_env.module.load_state(saved)
    assert game_env.state.scenario == "standard"


def test_c14_funds_bars(game_env):
    s = game_env.state
    s.lifetime_revenue, s.lifetime_build_spend = 200.0, 50.0
    game_env.module.render()
    assert game_env.elements["funds-bar-revenue"].style.width == "100%"
    assert game_env.elements["funds-bar-build"].style.width == "25%"
    assert game_env.elements["funds-bar-disruption"].style.width == "0%"


def test_c24_pulse_on_50_percent_crossing(game_env):
    game_env.build("solar")
    bar = game_env.elements["emissions-bar"]
    assert "meter-pulse" in bar.classList
    game_env.timers.flush()
    assert "meter-pulse" not in bar.classList


def test_c15_summary_has_fallback_and_calls_hook(game_env):
    game_env.toggle_summary_panel()
    assert "isn't available yet" in game_env.elements["summary-panel"].innerHTML
    calls = []

    class W:
        gridCompare = staticmethod(lambda e, r: calls.append((e, r)))

    sys.modules["js"].window = W()
    try:
        game_env.module.render()
    finally:
        del sys.modules["js"].window
    assert calls == [(0.0, 1)]
