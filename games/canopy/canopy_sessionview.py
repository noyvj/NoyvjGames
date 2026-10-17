"""Saved playstyle runs and their comparison, the session summary panel and the stats line."""

import json

from js import document

import canopy_runstate as runstate
from canopy_challenge import _update_scenario_best, render_scenario_best
from canopy_charts import render_forest_log_panels, render_report_card, render_timeline_chart
from canopy_comfort import render_coach_hints
from canopy_community import render_community_note
from canopy_helpers import _read_local_storage_item, _write_local_storage_item, fmt_num
from canopy_labui import render_lab
from canopy_layout import render_carbon, render_layout_editor, render_lifetime_stats
from canopy_lifetime import render_forest_rank, render_my_forests
from canopy_plotsheet import render_plot_note_input
from canopy_records import _maybe_update_personal_best, render_legacy_bonus, render_personal_best
from canopy_rules import PRESERVED, RECOVERED
from canopy_stakeholders import render_faces, render_request_history
from canopy_summary import (
    counterfactual_message, render_replay, session_history_svg, share_snippet, state_breakdown_text,
)
from canopy_valuation import (
    active_plot_count, biodiversity_rate_per_tick, standing_forest_value, state_breakdown,
    total_biodiversity,
)


# B7 (planning/TODO.md "Per-game: Canopy"): save/compare two named
# playstyle runs. Per-browser via localStorage -- same mechanism and same
# "deliberately NOT part of get_state()" reasoning as B14's personal
# best, since these are standalone comparison snapshots a player takes on
# purpose, not live state to resume a session from. reset_session() does
# NOT clear these, matching personal_best's own cross-session lifetime.
PLAYSTYLE_RUNS_STORAGE_KEY = "canopy_playstyle_runs_v1"
PLAYSTYLE_RUN_SLOTS = ("a", "b")


def load_playstyle_runs():
    raw = _read_local_storage_item(PLAYSTYLE_RUNS_STORAGE_KEY)
    if not raw:
        return {"a": None, "b": None}
    try:
        data = json.loads(raw)
        return {slot: data.get(slot) for slot in PLAYSTYLE_RUN_SLOTS}
    except (ValueError, TypeError, AttributeError):
        return {"a": None, "b": None}


runstate.playstyle_runs = load_playstyle_runs()


def _playstyle_run_snapshot():
    """What gets frozen into a slot -- a plain, JSON-safe dict of the
    stats worth comparing across two different playstyles (one leaning
    quick-clear, one leaning preserve-everything, say)."""
    counts = state_breakdown()
    return {
        "income": runstate.total_income,
        "standing_value": standing_forest_value(),
        "biodiversity": total_biodiversity(),
        "plots_standing": counts[PRESERVED] + counts[RECOVERED],
        "plots_total": active_plot_count(),
        "grid_size": runstate.current_grid_size,
    }


def save_playstyle_run(slot, event=None):
    if slot not in PLAYSTYLE_RUN_SLOTS:
        return False
    runstate.playstyle_runs = dict(runstate.playstyle_runs)
    runstate.playstyle_runs[slot] = _playstyle_run_snapshot()
    _write_local_storage_item(PLAYSTYLE_RUNS_STORAGE_KEY, json.dumps(runstate.playstyle_runs))
    render_session_summary()
    return True


def on_save_playstyle_run_a(event=None):
    save_playstyle_run("a")


def on_save_playstyle_run_b(event=None):
    save_playstyle_run("b")


def _playstyle_stat_row(label, key):
    def cell(run):
        if run is None:
            return "—"
        value = run[key]
        return f"{value:.1f}" if isinstance(value, float) else str(value)

    return (
        f"<tr><td>{label}</td>"
        f"<td>{cell(runstate.playstyle_runs.get('a'))}</td>"
        f"<td>{cell(runstate.playstyle_runs.get('b'))}</td></tr>"
    )


def playstyle_comparison_html():
    """"" (rather than an empty/degenerate <table>) once neither slot has
    ever been saved -- render_playstyle_comparison() shows a plain prompt
    instead in that case, same convention as session_history_svg()."""
    if runstate.playstyle_runs.get("a") is None and runstate.playstyle_runs.get("b") is None:
        return ""

    def plots_cell(run):
        return "—" if run is None else f"{run['plots_standing']}/{run['plots_total']}"

    rows = "".join(
        [
            _playstyle_stat_row("Income", "income"),
            _playstyle_stat_row("Standing value", "standing_value"),
            _playstyle_stat_row("Biodiversity", "biodiversity"),
            "<tr><td>Plots standing</td>"
            f"<td>{plots_cell(runstate.playstyle_runs.get('a'))}</td>"
            f"<td>{plots_cell(runstate.playstyle_runs.get('b'))}</td></tr>",
        ]
    )
    return (
        '<table class="playstyle-comparison-table">'
        "<thead><tr><th></th><th>Run A</th><th>Run B</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def render_playstyle_comparison():
    container = document.getElementById("session-summary-playstyle-comparison")
    if container is None:
        return
    html = playstyle_comparison_html()
    if html:
        container.innerHTML = html
    else:
        container.innerHTML = ""
        container.innerText = "Save a run below to start comparing playstyles."


def on_toggle_session_summary(event=None):
    runstate.session_summary_open = not runstate.session_summary_open
    render_session_summary()


def render_session_summary():
    toggle = document.getElementById("session-summary-toggle-button")
    panel = document.getElementById("session-summary-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Session Summary" if runstate.session_summary_open else "\U0001F4CB Session Summary"
    panel.hidden = not runstate.session_summary_open
    if not runstate.session_summary_open:
        return

    document.getElementById("session-summary-counterfactual").innerText = counterfactual_message()

    sparkline_container = document.getElementById("session-summary-sparkline")
    svg = session_history_svg()
    if svg:
        sparkline_container.innerHTML = svg
    else:
        sparkline_container.innerHTML = ""
        sparkline_container.innerText = "Not enough time has passed yet to chart a trend."

    document.getElementById("session-summary-share-text").innerText = share_snippet()
    render_playstyle_comparison()
    render_report_card()
    render_timeline_chart()
    render_replay()
    render_forest_log_panels()
    render_request_history()
    render_faces()
    render_carbon()
    render_layout_editor()
    render_community_note()
    render_lifetime_stats()
    render_my_forests()
    render_lab()
    render_forest_rank()
    render_coach_hints()
    _update_scenario_best()
    render_scenario_best()
    render_plot_note_input()


def comparison_message(income, standing_value):
    """The hope-angle payoff: a plain-language read on how short-term
    harvesting stacks up against the value of what's still standing."""
    if income == 0 and standing_value == 0:
        return "Nothing harvested or grown yet — clear a plot for quick income, or leave one standing to watch its value compound."
    if standing_value > income:
        return (
            f"Your standing forest ({standing_value:.1f}) is worth more than everything "
            f"you've harvested ({income:.1f}) — patience is compounding."
        )
    if income > standing_value:
        return (
            f"You've harvested more ({income:.1f}) than your forest currently holds "
            f"({standing_value:.1f}) — quick income, but nothing left compounding."
        )
    return f"Harvested income and standing forest value are evenly matched, at {income:.1f}."


def render_stats():
    standing_value = standing_forest_value()
    document.getElementById("income-display").innerText = f"Harvested income: {fmt_num(runstate.total_income)}"
    document.getElementById("standing-value-display").innerText = f"Standing forest value: {fmt_num(standing_value)}"
    document.getElementById("biodiversity-display").innerText = (
        f"Biodiversity: {fmt_num(total_biodiversity())} (+{biodiversity_rate_per_tick():.2f}/tick)"
    )
    document.getElementById("comparison-message").innerText = comparison_message(runstate.total_income, standing_value)
    document.getElementById("state-breakdown-display").innerText = state_breakdown_text()
    document.getElementById("community-relations-display").innerText = (
        f"Community relations: {runstate.community_relations}/100"
    )
    _maybe_update_personal_best()
    render_personal_best()
    render_legacy_bonus()
