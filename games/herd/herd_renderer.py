"""render(): the one function that redraws the whole page from the farm.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import (
    BASE_COUPLING_RATIO, DECOUPLING_MEASURES, HERD_INCOME_PER_UNIT, MAX_HAZE_OPACITY, MAX_PLANT_BASED_FRACTION,
    MAX_PRESSURE, PLANT_BASED_EMISSIONS_MULTIPLIER, PLANT_PIVOT_COST, POULTRY_BASE_RATIO, POULTRY_INCOME_PER_UNIT,
)
from herd_model import pressure_scale
from herd_blind import blind_hidden, render_blind_run
from herd_visuals import (
    _maybe_update_record_coupling_ratio, coupling_gauge_svg, methane_trend_graph_svg,
    real_world_comparison_chart_svg, render_record_coupling_ratio,
)
from herd_messages import (
    _request_comparison, certification_message, combined_decoupling_message,
    counterfactual_comparison_message, grow_consequence_message, real_world_comparison_message,
    render_info_page,
)
from herd_achievements import update_achievements_display
from herd_pasture import update_pasture_visual
from herd_changelog import update_changelog_display
from herd_sandbox import render_sandbox
from herd_barns import render_barns, render_golden_cow
from herd_loadouts import render_audit, render_loadouts
from herd_rules_ui import render_rules
from herd_ledger import ghost_graph_data, render_ghost, render_ledger
from herd_extras import render_extras
from herd_collection import _sync_collection, render_progress_extras
from herd_round import bulk_button_label, render_round_extras
from herd_explain import render_explain
from herd_planner import render_planner
from herd_pins import render_pins
from herd_mixer import render_mixer
from herd_family import render_family_story
from herd_profile import render_profile
from herd_summary import report_card_html


def render():
    _sync_collection()
    render_info_page()
    _maybe_update_record_coupling_ratio()
    coupling_fraction = runstate.farm.coupling_ratio() / BASE_COUPLING_RATIO
    document.getElementById("coupling-gauge").innerHTML = coupling_gauge_svg(
        coupling_fraction, None if blind_hidden() else runstate.record_coupling_ratio
    )
    document.getElementById("coupling-gauge-label").innerText = (
        f"Emissions per herd unit: {runstate.farm.coupling_ratio():.2f} methane/round"
    )
    render_record_coupling_ratio()

    document.getElementById("haze-overlay").style.opacity = (
        f"{(runstate.farm.pressure_fraction() / MAX_PRESSURE) * MAX_HAZE_OPACITY:.3f}"
    )

    document.getElementById("round-display").innerText = f"Round {runstate.farm.round_number}"
    document.getElementById("funds-display").innerText = "Funds: unlimited (sandbox)" if runstate.sandbox_active else f"Funds: {runstate.farm.funds:.0f}"
    document.getElementById("herd-display").innerText = f"Herd size: {runstate.farm.herd_size}"
    document.getElementById("methane-display").innerText = f"Methane: {runstate.farm.methane:.0f}"
    document.getElementById("coupling-display").innerText = (
        f"Coupling ratio: {runstate.farm.coupling_ratio():.2f} methane/herd/round"
    )
    document.getElementById("pressure-display").innerText = (
        f"Market/regulatory pressure: {runstate.farm.pressure_fraction() * 100:.0f}% income loss"
    )
    document.getElementById("methane-bar").style.width = (
        f"{min(1.0, runstate.farm.methane / pressure_scale()) * 100:.0f}%"
    )
    document.getElementById("score-display").innerText = "Score: not counted (sandbox)" if runstate.sandbox_active else f"Score: {runstate.farm.score():.0f}"

    # GF-20: farm event card
    event_el = document.getElementById("farm-event-card")
    if runstate.farm.event_active and not runstate.farm.event_choice_made:
        event_el.hidden = False
        document.getElementById("event-text").innerText = runstate.farm.event_data["text"]
        document.getElementById("event-choice-a").innerText = runstate.farm.event_data["choice_a"]["label"]
        document.getElementById("event-choice-b").innerText = runstate.farm.event_data["choice_b"]["label"]
    else:
        event_el.hidden = True

    grow_cost = runstate.farm.grow_herd_cost()
    grow_button = document.getElementById("grow-herd-button")
    grow_button.innerText, grow_button.disabled = bulk_button_label("herd", "Grow Herd", grow_cost, ".0f")
    # F9 — consequence preview next to the Grow Herd button.
    document.getElementById("grow-consequence-preview").innerText = grow_consequence_message()

    for measure, spec in DECOUPLING_MEASURES.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            runstate.farm.decoupling_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        cost = runstate.farm.decoupling_cost(measure)
        button.innerText, button.disabled = bulk_button_label(measure, spec["label"], cost, "g")

    document.getElementById("decoupling-summary-display").innerText = (
        f"Decoupled: {runstate.farm.decoupled_fraction() * 100:.0f}% below baseline emissions per herd unit"
    )

    plant_fraction = runstate.farm.plant_based_fraction()
    document.getElementById("plant-pivot-count").innerText = str(runstate.farm.plant_pivot_investment)
    document.getElementById("plant-pivot-display").innerText = (
        f"{plant_fraction * 100:.0f}% of output shifted to plant-based production"
    )
    plant_pivot_button = document.getElementById("plant-pivot-invest-button")
    plant_pivot_button.innerText = f"Plant-Based Pivot ({PLANT_PIVOT_COST})"
    plant_pivot_button.disabled = runstate.farm.funds < PLANT_PIVOT_COST or plant_fraction >= MAX_PLANT_BASED_FRACTION

    # F8 — combined efficiency + plant-pivot readout.
    document.getElementById("combined-decoupling-display").innerText = combined_decoupling_message()

    # F14 — min/max labels behind the coupling gauge. coupling_ratio()
    # only ever decreases as investment counts rise (they never go down),
    # so the session's best-ever value is simply the current one, and the
    # worst-ever is always the fixed baseline.
    document.getElementById("gauge-range-display").innerText = (
        "Session best and baseline markers are hidden during a blind run."
        if blind_hidden() else f"Session best: {runstate.farm.coupling_ratio():.2f}  |  Baseline: {BASE_COUPLING_RATIO:.2f}"
    )

    # F15 — the real-world 42% comparison.
    document.getElementById("real-world-comparison-display").innerText = real_world_comparison_message()
    document.getElementById("real-world-comparison-chart").innerHTML = real_world_comparison_chart_svg()

    document.getElementById("certification-display").innerText = certification_message()

    # F7 — methane-over-rounds trend graph.
    document.getElementById("methane-trend-graph").innerHTML = methane_trend_graph_svg(runstate.farm.methane_history, ghost_graph_data())
    render_ghost()  # Z-3e

    # F1/F13 — live pure-growth counterfactual + persistent baseline-farm card.
    document.getElementById("counterfactual-comparison-display").innerText = counterfactual_comparison_message()
    blind = blind_hidden()
    document.getElementById("baseline-herd-display").innerText = f"Herd size: {runstate.farm.herd_size}"
    document.getElementById("baseline-funds-display").innerText = "Funds: hidden" if blind else f"Funds: {runstate.farm.counterfactual_funds:.0f}"
    document.getElementById("baseline-methane-display").innerText = "Methane: hidden" if blind else f"Methane: {runstate.farm.counterfactual_methane:.0f}"
    document.getElementById("baseline-score-display").innerText = "Score: hidden" if blind else f"Score: {runstate.farm.counterfactual_score():.0f}"

    # F3 — report card panel, kept in sync if left open across a render. The toggle's label is
    # always set so a fresh page never shows the "Loading..." placeholder from index.html.
    document.getElementById("report-card-toggle-button").innerText = (
        "Hide Report Card" if runstate.report_card_open else "📊 Report Card"
    )
    if runstate.report_card_open:
        document.getElementById("report-card-panel").innerHTML = report_card_html()
        _request_comparison()  # F7 -- re-asks the hook; JS side caches/dedupes

    # Achievements panel, kept in sync if left open across a render.
    update_achievements_display()

    # "What's New" changelog panel, kept in sync if left open across a render.
    update_changelog_display()

    # F2 — pasture visual cow count scales with real herd size.
    update_pasture_visual()

    render_extras()
    render_progress_extras()
    render_round_extras()
    render_explain()
    render_rules()
    render_planner()
    render_ledger()
    render_pins()
    render_mixer()
    render_family_story()
    render_profile()
    render_barns()
    render_golden_cow()
    render_blind_run()
    render_loadouts()
    render_audit()
    render_sandbox()

    # F-8: Mixed-herd allocation UI
    alloc_el = document.getElementById("allocation-control")
    if runstate.farm.poultry_unlocked():
        alloc_el.hidden = False
        alloc = runstate.farm.allocation_poultry
        document.getElementById("allocation-value").innerText = f"{int(alloc * 100)}% Poultry"

        plant_frac = runstate.farm.plant_based_fraction()
        beef_part = (1 - alloc) * (1 - plant_frac)
        poultry_part = alloc * (1 - plant_frac)
        plant_part = plant_frac

        total = beef_part + poultry_part + plant_part or 1
        document.getElementById("alloc-beef").style.width = f"{beef_part / total * 100:.0f}%"
        document.getElementById("alloc-poultry").style.width = f"{poultry_part / total * 100:.0f}%"
        document.getElementById("alloc-plant").style.width = f"{plant_part / total * 100:.0f}%"

        beef_income = runstate.farm.herd_size * (1 - alloc) * HERD_INCOME_PER_UNIT * runstate.farm.certification_multiplier() * runstate.farm.welfare_multiplier()
        poultry_income = runstate.farm.herd_size * alloc * POULTRY_INCOME_PER_UNIT
        plant_income = runstate.farm.herd_size * plant_frac * HERD_INCOME_PER_UNIT * PLANT_BASED_EMISSIONS_MULTIPLIER
        total_income = beef_income + poultry_income + plant_income

        beef_methane = runstate.farm.herd_size * (1 - alloc) * BASE_COUPLING_RATIO
        poultry_methane = runstate.farm.herd_size * alloc * POULTRY_BASE_RATIO
        plant_methane = runstate.farm.herd_size * plant_frac * PLANT_BASED_EMISSIONS_MULTIPLIER
        total_methane = beef_methane + poultry_methane + plant_methane

        welfare = runstate.farm.welfare()

        document.getElementById("alloc-income").innerText = f"Income: {total_income:.0f}"
        document.getElementById("alloc-methane").innerText = f"Methane: {total_methane:.0f}"
        document.getElementById("alloc-welfare").innerText = f"Welfare: {welfare:.0f}"
    else:
        alloc_el.hidden = True
