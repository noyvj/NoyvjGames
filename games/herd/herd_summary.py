"""The end-of-run report card and the copy-result fields.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_model import rules_unranked
from herd_blind import blind_hidden
from herd_messages import (
    COMPARE_FALLBACK, _request_comparison, beat_percentage_message, investment_summary_message,
    real_world_comparison_message, unranked_compare_note,
)
from herd_loadouts import audit_report_line
from herd_extras import policy_report_line
from herd_collection import RATING_TITLES, highlights_html, rating_index, rating_message
from herd_mixer import mixer_stats_message


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Herd, 412 score, Careful Rancher, round 9, ...". Read by the page's
    own inline script through pyodide.globals when the shared Copy result
    button is pressed, so it always matches the farm as it stands."""
    methane_avoided = max(0.0, runstate.farm.counterfactual_methane - runstate.farm.methane)
    stats = [
        RATING_TITLES[rating_index()][0],
        f"round {runstate.farm.round_number}",
        f"{runstate.farm.decoupled_fraction() * 100:.0f}% decoupled",
        "blind run" if blind_hidden() else f"{methane_avoided:.0f} methane avoided",
    ]
    if rules_unranked():
        stats.append("custom rules, unranked")
    return {"game": "Herd (practice sandbox)" if runstate.sandbox_active else "Herd", "score": round(runstate.farm.score()), "unit": "score", "stats": stats}


def report_card_html():
    """F3 — an on-demand end-of-session report card. Reuses the exact
    same counterfactual numbers as the live comparison (F1) and the
    baseline-farm card (F13); this just restates them with more
    breakdown, the same relationship Grid's Run Summary panel has to its
    own always-visible readouts."""
    gap = runstate.farm.score() - runstate.farm.counterfactual_score()
    methane_avoided = max(0.0, runstate.farm.counterfactual_methane - runstate.farm.methane)
    if blind_hidden():
        lines = [
            f"Round {runstate.farm.round_number} — your score: {runstate.farm.score():.0f}. The comparison with the pure-growth baseline is hidden during your blind run; reveal it from the Baseline Farm card whenever you like.",
            investment_summary_message(),
            policy_report_line(),
            mixer_stats_message(),
            real_world_comparison_message(),
        ]
        lines.insert(1, rating_message())
        body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
        return body + f'<p id="report-card-compare" class="status-line summary-line">{unranked_compare_note() if rules_unranked() else COMPARE_FALLBACK}</p>' + highlights_html()
    lines = [
        f"Round {runstate.farm.round_number} — your score: {runstate.farm.score():.0f} vs. pure-growth baseline: {runstate.farm.counterfactual_score():.0f}",
        f"Same herd size ({runstate.farm.herd_size}), but your methane is {runstate.farm.methane:.0f} vs. the baseline's {runstate.farm.counterfactual_methane:.0f} — {methane_avoided:.0f} avoided.",
        f"Your funds: {runstate.farm.funds:.0f} vs. baseline funds: {runstate.farm.counterfactual_funds:.0f} (baseline never spent on decoupling, but also never avoided any pressure).",
        (
            f"Net: decoupling investment is worth {gap:.0f} points to your score right now."
            if gap >= 0
            else f"Net: your score is currently {abs(gap):.0f} points behind the baseline — invest more in decoupling to close the gap."
        ),
        beat_percentage_message(),
        investment_summary_message(),
        policy_report_line(),
        mixer_stats_message(),
        real_world_comparison_message(),
    ]
    lines.insert(1, rating_message())
    if runstate.farm.audits_done:
        lines.insert(2, audit_report_line())
    body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
    # F7: filled in by index.html's window.herdCompare() when the shared
    # stats endpoint (planning/TODO.md Z1) is reachable; otherwise this
    # fallback text simply stays.
    compare_text = unranked_compare_note() if rules_unranked() else COMPARE_FALLBACK
    return body + f'<p id="report-card-compare" class="status-line summary-line">{compare_text}</p>' + highlights_html()


def on_toggle_report_card(event=None):
    runstate.report_card_open = not runstate.report_card_open
    update_report_card()


def update_report_card():
    toggle = document.getElementById("report-card-toggle-button")
    panel = document.getElementById("report-card-panel")
    toggle.innerText = "Hide Report Card" if runstate.report_card_open else "📊 Report Card"
    panel.hidden = not runstate.report_card_open
    if not runstate.report_card_open:
        return
    panel.innerHTML = report_card_html()
    _request_comparison()
