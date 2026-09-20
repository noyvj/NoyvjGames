"""Round-2 Drift items: I2, I4, I5, I6, I9, I11, I12, I14, I15, I16, I19, I21,
I23, I24, I27, I28, I30."""

from pathlib import Path


def _el(env, id_):
    return env.elements[id_]


def _play(env, rounds):
    for _ in range(rounds):
        env.advance_round()


# --- I4 ---
def test_accelerated_button_states_multiplier_visibly(game_env):
    game_env.elements["accelerated-severity-toggle-button"].dispatch("click", None)
    assert "2x" in _el(game_env, "accelerated-severity-toggle-button").innerText


# --- I6 ---
def test_trend_indicator_labels(game_env):
    m = game_env.module
    assert m.trend_indicator([10, 20, 30]) == "improving"
    assert m.trend_indicator([30, 20, 10]) == "declining"
    assert m.trend_indicator([50, 50.5]) == "plateauing"
    assert m.trend_indicator([]) == "plateauing"


def test_session_milestone_includes_trend(game_env):
    _play(game_env, 20)
    assert game_env.region.last_milestone_snapshot["trend"] in ("improving", "plateauing", "declining")
    assert game_env.region.last_milestone_snapshot["trend"] in _el(
        game_env, "session-milestone-display"
    ).innerText


def test_session_milestone_old_snapshot_without_trend(game_env):
    game_env.region.last_milestone_round = 20
    game_env.region.last_milestone_snapshot = {
        "total_arrivals": 1, "integrated_population": 1, "average_strain": 0.1, "wellbeing_score": 50,
    }
    msg = game_env.module.session_milestone_message(game_env.region)
    assert msg.endswith("wellbeing 50.")


# --- I9 ---
def test_forecast_lists_five_rounds_and_capacity_need(game_env):
    arrivals = game_env.module.forecast_arrivals(game_env.region)
    assert len(arrivals) == 5
    assert arrivals[0] == game_env.region.arrivals_this_round()
    assert arrivals[1] > arrivals[0]
    assert "would need to reach" in _el(game_env, "forecast-display").innerText


def test_forecast_accelerated_rises_faster(game_env):
    normal = game_env.module.forecast_arrivals(game_env.region)
    game_env.region.accelerated_severity_enabled = True
    fast = game_env.module.forecast_arrivals(game_env.region)
    assert fast[-1] > normal[-1]


def test_forecast_covered_message(game_env):
    game_env.region.capacity["housing"] = 1000
    game_env.module.render()
    assert "already covers" in _el(game_env, "forecast-display").innerText


# --- I30 ---
def test_capacity_milestone_no_pace_yet(game_env):
    assert "invest to set a pace" in _el(game_env, "capacity-milestone-display").innerText


def test_capacity_milestone_estimate(game_env):
    game_env.invest("housing")
    game_env.invest("housing")  # 20 capacity
    _play(game_env, 2)
    text = _el(game_env, "capacity-milestone-display").innerText
    assert "50 total capacity" in text and "3 rounds" in text  # 30 short at 10/round


# --- I27 ---
def test_roi_none_before_investment(game_env):
    assert game_env.region.investment_roi() is None
    assert "nothing has been returned" in _el(game_env, "roi-display").innerText


def test_total_invested_and_roi(game_env):
    game_env.invest("services")
    game_env.invest("housing")
    assert game_env.region.total_invested() == 40
    game_env.region.cumulative_integration_contribution = 20
    assert game_env.region.investment_roi() == 0.5


# --- I28 / I12 ---
def test_tooltips_set(game_env):
    assert "critical from 60%" in _el(game_env, "strain-consequence-display").title
    assert "passive comparison" in _el(game_env, "control-region-contrast-display").title


# --- I14 ---
def test_gauge_target_note_names_threshold(game_env):
    for gid in ("service-quality", "economic-health", "social-cohesion"):
        assert "70" in _el(game_env, f"{gid}-target").innerText


# --- I24 ---
def test_subscore_log_grows_and_arrows_show(game_env):
    assert _el(game_env, "service-quality-trend").innerText == ""
    game_env.invest("services")
    _play(game_env, 3)
    assert len(game_env.region.subscore_log) == 3
    assert _el(game_env, "social-cohesion-trend").innerText in ("▲", "▶", "▼")


def test_subscore_arrow_directions(game_env):
    m = game_env.module
    up = [{"service": 10}, {"service": 30}]
    down = [{"service": 30}, {"service": 10}]
    assert m.subscore_arrow(up, "service") == "▲"
    assert m.subscore_arrow(down, "service") == "▼"
    assert m.subscore_arrow(up[:1], "service") == ""


# --- I2 ---
def test_trend_graph_control_line_optional(game_env):
    m = game_env.module
    base = m.trend_graph_svg([0.1, 0.2], [50, 60])
    assert base.count("<polyline") == 2
    withc = m.trend_graph_svg([0.1, 0.2], [50, 60], [30, 20])
    assert withc.count("<polyline") == 3 and "trend-line--control" in withc
    assert withc.count("<circle") == base.count("<circle")


def test_render_draws_control_line_after_two_rounds(game_env):
    _play(game_env, 3)
    assert "trend-line--control" in _el(game_env, "trend-graph").innerHTML


# --- I11 ---
def test_thriving_vignette_hidden_until_thriving(game_env):
    assert _el(game_env, "thriving-vignette-box").hidden is True
    game_env.region.thriving_round = 5
    game_env.module.render()
    assert _el(game_env, "thriving-vignette-box").hidden is False
    assert "capacity built before" in _el(game_env, "thriving-vignette-display").innerText


# --- I16 ---
def test_recovery_badge(game_env):
    m = game_env.module
    r = game_env.region
    r.funds = 5000
    r.total_arrivals = 10
    r.integrated_population = 10
    r.strain_log = [0.0]
    assert r.wellbeing_score() >= 90
    assert "recovery" in m.recovery_badge_text(r, True)
    assert m.recovery_badge_text(r, False) is None
    r.funds = 0
    assert m.recovery_badge_text(r, True) is None


# --- I15 ---
def test_crisis_start_toggle_round_one_only(game_env):
    _el(game_env, "crisis-start-toggle-button").dispatch("click", None)
    assert game_env.region.crisis_start_enabled
    assert game_env.region.funds == game_env.module.CRISIS_START_FUNDS
    assert game_env.region.strain_fraction() == 1.0
    _el(game_env, "crisis-start-toggle-button").dispatch("click", None)
    assert game_env.region.funds == game_env.module.STARTING_FUNDS
    assert game_env.region.total_arrivals == 0


def test_crisis_start_locked_after_first_round(game_env):
    game_env.advance_round()
    assert _el(game_env, "crisis-start-toggle-button").disabled is True
    _el(game_env, "crisis-start-toggle-button").dispatch("click", None)
    assert not game_env.region.crisis_start_enabled


def test_crisis_start_locked_after_investing(game_env):
    game_env.invest("housing")
    assert game_env.region.set_crisis_start(True) is False


# --- I19 ---
def test_reallocate_moves_capacity_with_cost_and_loss(game_env):
    m = game_env.module
    game_env.invest("housing")  # 10 housing
    funds = game_env.region.funds
    _el(game_env, "realloc-from").value = "housing"
    _el(game_env, "realloc-to").value = "services"
    _el(game_env, "realloc-button").dispatch("click", None)
    r = game_env.region
    assert r.capacity["housing"] == 0
    assert r.capacity["services"] == 10 * (1 - m.REALLOCATION_LOSS_FRACTION)
    assert r.funds == funds - m.REALLOCATION_FUNDS_COST


def test_reallocate_rejects_invalid(game_env):
    r = game_env.region
    assert r.reallocate("housing", "services") is False  # nothing to move
    r.capacity["housing"] = 10
    assert r.reallocate("housing", "housing") is False
    assert r.reallocate("housing", "bogus") is False
    r.funds = 1
    assert r.reallocate("housing", "services") is False


# --- I21 ---
def test_coda_control_comparison(game_env):
    game_env.invest("services")
    _play(game_env, 5)
    game_env.toggle_coda()
    text = _el(game_env, "coda-control-display").innerText
    assert "passive region" in text


# --- I5 ---
def test_coda_legacy_choice_flavors_text_only(game_env):
    before = game_env.region.wellbeing_score()
    _el(game_env, "coda-legacy-economy-button").dispatch("click", None)
    assert game_env.region.coda_legacy_choice == "economy"
    assert "Local economy" in _el(game_env, "coda-legacy-display").innerText
    assert game_env.region.wellbeing_score() == before


# --- I23 ---
def test_region_name_carried_into_coda(game_env):
    _el(game_env, "region-name-input").value = "  Harbour Vale  "
    _el(game_env, "region-name-input").dispatch("change", None)
    assert game_env.region.region_name == "Harbour Vale"
    game_env.invest("services")
    _play(game_env, 5)
    game_env.toggle_coda()
    assert _el(game_env, "coda-message-display").innerText.startswith("Harbour Vale: ")


def test_region_name_truncated(game_env):
    _el(game_env, "region-name-input").value = "x" * 100
    _el(game_env, "region-name-input").dispatch("change", None)
    assert len(game_env.region.region_name) == 30


# --- persistence ---
def test_new_fields_round_trip(game_env):
    _el(game_env, "region-name-input").value = "Vale"
    _el(game_env, "region-name-input").dispatch("change", None)
    _el(game_env, "coda-legacy-community-button").dispatch("click", None)
    _el(game_env, "crisis-start-toggle-button").dispatch("click", None)
    game_env.advance_round()
    state = game_env.module.get_state()
    game_env.region.region_name = ""
    game_env.region.subscore_log = []
    assert game_env.module.load_state(state)
    assert game_env.region.region_name == "Vale"
    assert game_env.region.coda_legacy_choice == "community"
    assert game_env.region.crisis_start_enabled is True
    assert len(game_env.region.subscore_log) == 1


def test_old_save_without_new_fields_loads(game_env):
    old = {"round_number": 4, "funds": 100}
    assert game_env.module.load_state(old)
    assert game_env.region.region_name == ""
    assert game_env.region.subscore_log == []
    assert game_env.region.coda_legacy_choice is None


def test_bad_new_field_values_ignored(game_env):
    game_env.module.load_state(
        {"region_name": 5, "coda_legacy_choice": "evil", "subscore_log": [1, {"service": 5}]}
    )
    assert game_env.region.region_name == ""
    assert game_env.region.coda_legacy_choice is None
    assert game_env.region.subscore_log == [{"service": 5}]


def test_html_declares_every_new_element():
    html = (Path(__file__).resolve().parent.parent / "index.html").read_text()
    for id_ in ("crisis-start-toggle-button", "realloc-button", "region-name-input",
                "forecast-display", "roi-display", "coda-control-display"):
        assert f'id="{id_}"' in html
