"""Round-7 pass (2026-10-11): trend-line checkboxes (C-12), the ghost run (GC-9), table views (C-19) and the
display-preference store they share."""
import json

from .test_career import _install_storage, _play


class _Event:
    def __init__(self, target):
        self.target = target


def _tick(game_env, element_id, checked):
    el = game_env.elements[element_id]
    el.checked = checked
    el.dispatch("change", _Event(el))


def _rounds(game_env, n=6):
    game_env.state.plant_counts["solar"] = 5
    game_env.state.plant_counts["coal"] = 3
    _play(game_env, n)
    game_env.module.render()


def _record(g, rounds, clean_start, clean_step, score=80.0):
    clean = [min(100, int(clean_start + clean_step * i)) for i in range(rounds)]
    return g._validate_run_record({
        "scenario": "standard", "grade": "B", "points": 3, "rounds": rounds, "score": score,
        "clean": g._thin(clean), "funds_series": g._thin([400 + 20 * i for i in range(rounds)]),
        "demand_series": g._thin([100 + 10 * i for i in range(rounds)]),
    })


# --- the preference store -------------------------------------------------

def test_prefs_default_and_validate(game_env):
    g = game_env.module
    assert g.prefs == g.PREF_DEFAULTS
    out = g.validate_prefs({"trend_funds": True, "trend_cost": "yes", "unit": "mw", "number_format": "weird", "x": 1})
    assert out["trend_funds"] is True and out["trend_cost"] is True  # a non-bool falls back to the default
    assert out["unit"] == "mw" and out["number_format"] == "full" and "x" not in out
    assert g.validate_prefs("junk") == g.PREF_DEFAULTS


def test_set_pref_saves_and_rejects_bad_values(game_env):
    g = game_env.module
    storage = _install_storage()
    assert g.set_pref("trend_funds", True) is True
    assert json.loads(storage.data[g.PREFS_STORAGE_KEY])["trend_funds"] is True
    assert g.set_pref("trend_funds", "yes") is False
    assert g.set_pref("nope", True) is False
    assert g.set_pref("unit", "furlongs") is False and g.set_pref("unit", "mw") is True
    assert g.prefs["trend_funds"] is True


def test_prefs_are_not_in_the_save(game_env):
    g = game_env.module
    g.set_pref("trend_funds", True)
    assert not any("pref" in key or key.startswith("trend_") for key in g.get_state())


# --- C-12 checkboxes -------------------------------------------------------

def test_default_graph_is_the_original_three_lines(game_env):
    _rounds(game_env)
    html = game_env.elements["trend-graph"].innerHTML
    assert html.count("<polyline") == 3
    assert "trend-line--funds" not in html
    assert game_env.elements["trend-graph-message"].innerText == game_env.module.TREND_DEFAULT_MESSAGE
    assert game_env.elements["trend-show-emissions"].checked is True
    assert game_env.elements["trend-show-funds"].checked is False


def test_checkbox_hides_a_line_but_keeps_the_best_marker(game_env):
    _rounds(game_env)
    assert "trend-best-marker" in game_env.elements["trend-graph"].innerHTML
    _tick(game_env, "trend-show-emissions", False)
    html = game_env.elements["trend-graph"].innerHTML
    assert "trend-line--emissions" not in html and "trend-best-marker" in html
    assert game_env.module.prefs["trend_emissions"] is False
    # Every line off: still a diamond, plus a sentence saying so.
    for key in ("cost", "benchmark"):
        _tick(game_env, f"trend-show-{key}", False)
    html = game_env.elements["trend-graph"].innerHTML
    assert "<polyline" not in html and "trend-best-marker" in html
    assert "No lines are switched on" in game_env.elements["trend-graph-message"].innerText


def test_funds_demand_and_clean_lines_can_be_added(game_env):
    _rounds(game_env)
    for key in ("funds", "demand", "clean"):
        _tick(game_env, f"trend-show-{key}", True)
    html = game_env.elements["trend-graph"].innerHTML
    for key in ("funds", "demand", "clean"):
        assert f"trend-line trend-line--{key}" in html
        assert f"trend-point--{key}" in html
    assert html.count("<polyline") == 6
    assert "Showing" in game_env.elements["trend-graph-message"].innerText
    assert "%" in html  # the clean-share tooltips are in percent


def test_hovered_values_match_the_run(game_env):
    _rounds(game_env, 4)
    s = game_env.state
    svg = game_env.module.trend_graph_svg(
        s.emissions_history, s.avg_renewable_cost_history, s.global_reference_emissions_history,
        s.clean_fraction_log, visible={"funds"}, funds_history=s.funds_history, demand_history=s.demand_history,
    )
    assert f"Round 4 -- Funds: {s.funds_history[-1]:.0f}" in svg
    assert svg.count("<polyline") == 1


def test_a_series_of_the_wrong_length_is_skipped_not_a_crash(game_env):
    g = game_env.module
    svg = g.trend_graph_svg([1, 2, 3], [5, 4, 3], [2, 3, 4], [0.1, 0.5, 0.3], visible={"funds", "demand", "emissions"},
                            funds_history=[], demand_history=[1, 2])
    assert svg.count("<polyline") == 1  # only emissions drew


def test_the_old_call_shape_still_works(game_env):
    svg = game_env.module.trend_graph_svg([0.0, 10.0, 20.0], [150.0, 100.0, 60.0], [0.0, 15.0, 30.0])
    assert svg.count("<polyline") == 3


def test_checkbox_state_follows_a_loaded_preference(game_env):
    g = game_env.module
    g.prefs["trend_demand"] = True
    g.render()
    assert game_env.elements["trend-show-demand"].checked is True


# --- GC-9 ghost run ----------------------------------------------------------

def test_ghost_value_reads_short_and_long_runs(game_env):
    g = game_env.module
    assert g.ghost_value([10, 20, 30], 3, 2) == 20
    assert g.ghost_value([10, 20, 30], 3, 4) is None and g.ghost_value([10, 20, 30], 3, 0) is None
    long_series = list(range(30))  # a 59-round run thinned to 30 points
    assert g.ghost_value(long_series, 59, 1) == 0 and g.ghost_value(long_series, 59, 59) == 29
    assert g.ghost_value([], 5, 1) is None


def test_ghost_record_is_the_best_finished_run(game_env):
    g = game_env.module
    assert g.ghost_record() is None
    g.career["history"] = [_record(g, 8, 10, 5, score=40.0), _record(g, 10, 10, 8, score=90.0), _record(g, 6, 5, 2, score=70.0)]
    ghost = g.ghost_record()
    assert ghost["score"] == 90.0 and ghost["rounds"] == 10 and ghost["label"].startswith("Run ")


def test_ghost_lines_and_delta_text(game_env):
    g = game_env.module
    g.career["history"] = [_record(g, 10, 20, 8, score=88.0)]
    _rounds(game_env, 6)
    _tick(game_env, "trend-show-clean", True)
    _tick(game_env, "trend-show-funds", True)
    assert "trend-line--clean-ghost" not in game_env.elements["trend-graph"].innerHTML  # ghost is off
    assert game_env.elements["trend-ghost-note"].hidden is True
    _tick(game_env, "trend-show-ghost", True)
    html = game_env.elements["trend-graph"].innerHTML
    assert "trend-line--clean-ghost" in html and "trend-line--funds-ghost" in html
    note = game_env.elements["trend-ghost-note"]
    assert note.hidden is False
    assert "Ghost: Run" in note.innerText and "At round 6 your clean share" in note.innerText
    assert "Funds:" in note.innerText


def test_ghost_without_a_finished_run_says_so(game_env):
    _rounds(game_env, 3)
    _tick(game_env, "trend-show-ghost", True)
    assert "No finished run to race yet" in game_env.elements["trend-ghost-note"].innerText
    assert "ghost" not in game_env.elements["trend-graph"].innerHTML.lower().replace("trend-line--ghost", "")


def test_ghost_that_ended_early_is_explained(game_env):
    g = game_env.module
    g.career["history"] = [_record(g, 3, 20, 8)]
    _rounds(game_env, 6)
    g.set_pref("trend_ghost", True)
    g.render()
    assert "ended before round 6" in game_env.elements["trend-ghost-note"].innerText


def test_ghost_needs_a_visible_line_to_draw_on(game_env):
    g = game_env.module
    g.career["history"] = [_record(g, 10, 20, 8)]
    _rounds(game_env, 4)
    g.set_pref("trend_ghost", True)
    g.render()
    assert "Switch on Clean share or Funds" in game_env.elements["trend-ghost-note"].innerText


# --- C-19 table view ---------------------------------------------------------------

def test_table_view_replaces_the_graph_with_numbers_and_a_description(game_env):
    _rounds(game_env, 5)
    _tick(game_env, "chart-table-view", True)
    html = game_env.elements["trend-graph"].innerHTML
    assert "<table" in html and "<svg" not in html and 'scope="row"' in html
    assert "(best round)" in html
    message = game_env.elements["trend-graph-message"].innerText
    assert message.startswith("Over 5 rounds:") and "emissions" in message
    _tick(game_env, "chart-table-view", False)
    assert "<svg" in game_env.elements["trend-graph"].innerHTML


def test_table_has_a_column_per_visible_line_and_caps_rows(game_env):
    g = game_env.module
    _rounds(game_env, 20)
    g.set_pref("table_view", True)
    g.set_pref("trend_funds", True)
    g.set_pref("trend_benchmark", False)
    g.render()
    html = game_env.elements["trend-graph"].innerHTML
    assert "<th scope=\"col\">Funds</th>" in html and "Global-average benchmark" not in html
    assert html.count("<tr>") == g.TREND_TABLE_MAX_ROWS + 1
    assert "last 15 of 20 rounds" in html


def test_table_view_with_too_few_rounds_keeps_the_waiting_message(game_env):
    game_env.module.set_pref("table_view", True)
    game_env.module.render()
    assert game_env.elements["trend-graph"].innerHTML == ""
    assert "Not enough rounds" in game_env.elements["trend-graph-message"].innerText


def test_trend_description_handles_no_lines(game_env):
    g = game_env.module
    series = g.trend_series([1, 2], [3, 2], [1, 2], [0.1, 0.2], [10, 20], [5, 6])
    assert "No lines" in g.trend_description(series, set())
    assert "clean share rose from 10% to 20%" in g.trend_description(series, {"clean"})


def test_table_view_also_tables_the_plant_mix_and_gauges(game_env):
    g = game_env.module
    _rounds(game_env, 3)
    assert game_env.elements["mix-table"].hidden is True and game_env.elements["gauge-table"].hidden is True
    assert game_env.elements["solar-mix-row"].hidden is False
    _tick(game_env, "chart-table-view", True)
    mix = game_env.elements["mix-table"]
    assert mix.hidden is False and "Share of emissions" in mix.innerHTML and "Solar" in mix.innerHTML
    assert game_env.elements["solar-mix-row"].hidden is True
    gauges = game_env.elements["gauge-table"].innerHTML
    assert "Emissions meter" in gauges and "Supply against demand" in gauges and "Disruption risk" in gauges
    _tick(game_env, "chart-table-view", False)
    assert game_env.elements["mix-table"].hidden is True and game_env.elements["solar-mix-row"].hidden is False
    assert g.prefs["table_view"] is False


def test_mix_table_on_an_empty_grid(game_env):
    assert "No generation on the grid yet" in game_env.module.mix_table_html()
