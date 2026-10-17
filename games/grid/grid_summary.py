"""The Run Summary panel, the copy-result fields and the summary toggle.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import SCENARIOS
from grid_career_actions import run_career_points
from grid_trend import business_as_usual_message, clean_trend_message
from grid_difficulty import DIFFICULTY_PRESETS, difficulty_preset_key


# C5 -- a dedicated, player-triggered "Run Summary" panel: a score
# breakdown (score, average clean share, the clean-trend comparison) plus
# the existing funds-breakdown numbers restated in one place, closing
# with the C17 business-as-usual counterfactual. Not tied to any hard
# "game over" state (Grid has none, by design -- see CLAUDE.md's "No hard
# fail-state" note) -- it's a summary of the run *so far*, available at
# any point, the same "on-demand panel" shape as the achievements panel
# above rather than a one-time end screen. Deliberately not persisted
# across save/load, same as achievements_open -- purely a this-session
# display preference, not game state.
def on_toggle_summary_panel(event=None):
    runstate.summary_panel_open = not runstate.summary_panel_open
    update_summary_panel()


COMPARE_FALLBACK = "Comparison with other players isn't available yet."


def _request_comparison():
    """C15: asks the page's optional JS hook (window.gridCompare, see
    index.html) to fill #summary-compare with a cross-player percentile.
    Absent hook (pytest, or a page without it) leaves the fallback text."""
    if runstate.sandbox_active:  # Z-18: a practice grid is never compared with real players
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "gridCompare", None)
    if hook is not None:
        hook(float(runstate.state.emissions), runstate.state.round_number)


def grade_message():
    """C5: operator-report letter grade vs. the real-world benchmark line."""
    grade = runstate.state.benchmark_grade()
    if grade is None:
        return "Operator grade: not graded yet -- play a round to get a benchmark to compare against."
    pct = runstate.state.emissions / runstate.state.global_reference_emissions * 100
    return (
        f"Operator grade: {grade} -- cumulative emissions are {pct:.0f}% of a "
        "global-average-mix grid's (A: under 20%, B: under 50%, C: under 80%, D: under 100%)."
    )


def projection_message(projection):
    """C25: the 'grid of the future' line."""
    shortfall = projection["demand"] - projection["capacity"]
    demand_note = (
        f"demand would reach {projection['demand']:.0f} against {projection['capacity']} capacity "
        f"({shortfall:.0f} short)"
        if shortfall > 0
        else f"capacity {projection['capacity']} would still cover demand of {projection['demand']:.0f}"
    )
    return (
        f"If you changed nothing for {projection['rounds']} more rounds: emissions would reach "
        f"{projection['emissions']:.0f} (all-coal would be {projection['bau_emissions']:.0f}), and {demand_note}."
    )


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Grid, 62 clean-grid score, round 14, operator grade B, ...". Read by
    the page's own inline script through pyodide.globals when the shared Copy
    result button is pressed, so it always matches the run as it stands."""
    stats = [f"round {runstate.state.round_number}"]
    grade = runstate.state.benchmark_grade()
    if grade is not None:
        stats.append(f"operator grade {grade}")
    stats.append(f"{runstate.state.emissions_avoided():.0f} emissions avoided")
    stats.append(f"resilience {runstate.state.resilience_score()}/100")
    return {
        "game": "Grid (practice sandbox)" if runstate.sandbox_active else "Grid",
        "score": round(runstate.state.score()),
        "unit": "clean-grid score",
        "stats": stats,
    }


def summary_panel_html():
    """C5: the Run Summary panel's content -- pure read of existing
    state/score/funds-breakdown/C17-counterfactual math, no new
    calculations invented here beyond formatting."""
    avg_clean_pct = runstate.state.average_clean_fraction() * 100
    preset = difficulty_preset_key()
    preset_label = DIFFICULTY_PRESETS[preset]["label"] if preset in DIFFICULTY_PRESETS else "Custom"
    bank_points, _ = run_career_points()
    lines = [
        f"Scenario: {SCENARIOS[runstate.state.scenario]['label']}. Difficulty: {preset_label}. Run seed: {runstate.state.seed}.",
        f"Round {runstate.state.round_number} — sustained clean-grid score: {runstate.state.score():.0f}/100",
        f"Average clean share across every round played: {avg_clean_pct:.0f}%",
        clean_trend_message(runstate.state.clean_trend()),
        (
            f"Funds so far — revenue: {runstate.state.lifetime_revenue:.0f}, spent building: "
            f"{runstate.state.lifetime_build_spend:.0f}, spent maintaining: "
            f"{runstate.state.lifetime_maintenance_spend:.0f}, lost to disruptions: "
            f"{runstate.state.lifetime_disruption_spend:.0f}."
        ),
        f"Best disruption-free streak so far: {runstate.state.best_clean_streak} round(s).",
        business_as_usual_message(runstate.state.emissions, runstate.state.bau_emissions),
        grade_message(),
        f"Grid resilience (diversification, separate from clean share): {runstate.state.resilience_score()}/100.",
        projection_message(runstate.state.projection()),
        (
            f"Career: {runstate.career['points']} point(s) earned over {runstate.career['runs']} finished run(s)"
            + (f"; finishing this run would bank {bank_points}." if bank_points > 0 else ".")
        ),
    ]
    body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
    # C15: filled in by index.html's window.gridCompare() when the shared
    # stats endpoint (planning/TODO.md Z1) is reachable; otherwise this
    # fallback text simply stays.
    return body + f'<p id="summary-compare" class="status-line summary-line">{COMPARE_FALLBACK}</p>'


def update_summary_panel():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Run Summary" if runstate.summary_panel_open else "📊 Run Summary"
    panel.hidden = not runstate.summary_panel_open
    if not runstate.summary_panel_open:
        return
    panel.innerHTML = summary_panel_html()
    _request_comparison()
