"""render(): the one function that redraws the whole page from the grid, plus the Career panel update and tree view it
calls back into (they call each other, so they stay together).
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document
from pyodide.ffi import create_proxy

import grid_runstate as runstate
from grid_rules import (
    AGE_WEAR_THRESHOLDS, CARBON_PRICING_FOSSIL_COST_MULTIPLIER, CAREER_MIN_ROUNDS, CAREER_TREE,
    DEMAND_RESPONSE_MIN_GROWTH, DEMAND_RESPONSE_REDUCTION_PER_LEVEL, EMISSIONS_METER_MAX, GENERATION_TYPES,
    PLANT_ICON, PLANT_LABEL, PLANT_TYPES, RENEWABLE_SUBSIDY_COST_MULTIPLIER, SCENARIOS,
    STEEP_DEMAND_GROWTH_MULTIPLIER, WEAR_TIER_GLYPH,
)
from grid_whatif import render_career_whatif
from grid_career_data import career_points_available
from grid_career_actions import unlock_career_perk
from grid_prefs import (
    format_amount, format_demand, render_confirmation_settings, render_number_settings, unit_suffix,
)
from grid_shadow import render_shadow
from grid_trend import (
    RENEWABLE_UNLOCK_BLURB, clean_trend_message, disruption_risk_message, global_comparison_message,
)
from grid_panels import render_info_page, update_changelog_display, update_weather_log_display
from grid_views import (
    demand_growth_arrow, demand_growth_title, render_chart_tables, render_chart_theme, render_trend,
    render_unlock_flash_setting, wear_tooltip,
)
from grid_messages import event_message, event_severity_class
from grid_difficulty import render_difficulty_preset
from grid_summary import update_summary_panel
from grid_skyline import render_skyline
from grid_achievement_cards import update_achievements_display
from grid_sandbox import render_sandbox_balance
from grid_fleet import render_fleet_overview
from grid_runsetup import render_run_setup_and_extras
from grid_coach import render_coach
from grid_arbitrage import _render_arbitrage_and_emergency
from grid_schematic import render_schematic
from grid_realgrid import render_real_grid, render_regional_grid
from grid_slots import render_slots
from grid_gridley import render_gridley, render_needle_gauge, render_rank
from grid_advance import render_auto_advance, render_round_animation_setting, render_round_recap
from grid_careerpanel import (
    _career_proxies, _js_window, _to_js, career_heatmap_html, career_history_charts_html, career_history_rows,
    career_lifetime_lines, career_next_perk_text, career_panel_lines, career_records_text,
    career_tree_summary_text,
)


def render():
    render_info_page()
    render_shadow()
    render_real_grid()
    render_regional_grid()
    update_achievements_display()
    update_changelog_display()
    update_weather_log_display()
    update_summary_panel()
    document.getElementById("round-display").innerText = f"Round {runstate.state.round_number}"
    demand_el = document.getElementById("demand-display")
    demand_el.innerText = f"Demand: {format_demand(runstate.state.demand)}{unit_suffix()} {demand_growth_arrow()}"
    demand_el.title = demand_growth_title()
    document.getElementById("streak-display").innerText = (
        f"Clean streak: {runstate.state.current_clean_streak} round(s) without a disruption "
        f"(best {runstate.state.best_clean_streak})"
    )
    document.getElementById("funds-display").innerText = (
        "Funds: unlimited (sandbox)" if runstate.sandbox_active else f"Funds: {format_amount(runstate.state.funds)}"
    )
    document.getElementById("capacity-display").innerText = (
        f"Capacity: {format_demand(runstate.state.total_capacity())}{unit_suffix()}"
    )
    document.getElementById("emissions-display").innerText = f"Emissions: {format_amount(runstate.state.emissions)}"
    document.getElementById("fossil-share-display").innerText = (
        f"Fossil share of grid: {runstate.state.fossil_share() * 100:.0f}%"
    )
    event_el = document.getElementById("event-display")
    event_el.innerText = event_message(runstate.state.last_event)
    event_el.className = event_severity_class(runstate.state.last_event)

    document.getElementById("score-display").innerText = f"Sustained clean-grid score: {runstate.state.score():.0f}"
    document.getElementById("trend-display").innerText = clean_trend_message(runstate.state.clean_trend())

    emissions_fraction = min(1.0, runstate.state.emissions / EMISSIONS_METER_MAX)
    document.getElementById("emissions-bar").style.width = f"{emissions_fraction * 100:.0f}%"
    document.getElementById("score-bar").style.width = f"{runstate.state.score():.0f}%"
    document.getElementById("disruption-risk-display").innerText = disruption_risk_message(
        runstate.state.disruption_probability(), runstate.state.disruption_severity()
    )

    # C16: opt-in difficulty toggle -- purely reflects the current setting,
    # never touches disruption math (see STEEP_DEMAND_GROWTH_MULTIPLIER's
    # comment above).
    steep_button = document.getElementById("steeper-demand-toggle-button")
    steep_button.innerText = (
        f"🔥 Steeper Demand Growth (x{STEEP_DEMAND_GROWTH_MULTIPLIER:g}): ON"
        if runstate.state.steeper_demand_growth_enabled
        else f"Steeper Demand Growth (x{STEEP_DEMAND_GROWTH_MULTIPLIER:g}): OFF"
    )
    if runstate.state.steeper_demand_growth_enabled:
        steep_button.classList.add("active")
    else:
        steep_button.classList.remove("active")

    weather_button = document.getElementById("weather-variability-toggle-button")
    weather_button.innerText = (
        "🌩️ Weather Variability: ON" if runstate.state.weather_variability_enabled else "Weather Variability: OFF"
    )
    if runstate.state.weather_variability_enabled:
        weather_button.classList.add("active")
    else:
        weather_button.classList.remove("active")

    render_trend()
    render_chart_theme()
    render_unlock_flash_setting()
    render_round_animation_setting()
    render_sandbox_balance()
    render_schematic()
    render_slots()
    render_chart_tables()
    render_fleet_overview()
    render_coach()
    render_rank()
    render_needle_gauge()
    render_gridley()
    render_skyline()
    render_number_settings()
    render_confirmation_settings()
    document.getElementById("global-comparison-message").innerText = global_comparison_message(
        runstate.state.emissions, runstate.state.global_reference_emissions
    )

    blurb_el = document.getElementById("renewable-blurb")
    blurb_el.innerText = RENEWABLE_UNLOCK_BLURB
    blurb_el.hidden = not runstate.state.renewable_unlocked

    aging_el = document.getElementById("aging-event-display")
    if runstate.state.last_aging_event is None:
        aging_el.innerText = "No aging breakdowns last round."
        aging_el.className = "event-display"
    else:
        plant_name = PLANT_LABEL[runstate.state.last_aging_event["plant"]]
        cost = runstate.state.last_aging_event["repair_cost"]
        aging_el.innerText = f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f})."
        aging_el.className = "event-display event-display--danger"

    # C13: a funds breakdown across the run so far, for transparency --
    # pure additive read of the lifetime_* totals above, no change to any
    # actual cost/refund math itself.
    document.getElementById("funds-breakdown-revenue").innerText = f"{runstate.state.lifetime_revenue:.0f}"
    document.getElementById("funds-breakdown-build").innerText = f"{runstate.state.lifetime_build_spend:.0f}"
    document.getElementById("funds-breakdown-maintenance").innerText = f"{runstate.state.lifetime_maintenance_spend:.0f}"
    document.getElementById("funds-breakdown-disruption").innerText = f"{runstate.state.lifetime_disruption_spend:.0f}"

    funds_values = {
        "revenue": runstate.state.lifetime_revenue,
        "build": runstate.state.lifetime_build_spend,
        "maintenance": runstate.state.lifetime_maintenance_spend,
        "disruption": runstate.state.lifetime_disruption_spend,
    }
    funds_max = max(funds_values.values()) or 1.0
    for key, value in funds_values.items():
        document.getElementById(f"funds-bar-{key}").style.width = f"{value / funds_max * 100:.0f}%"

    scenario_button = document.getElementById("scenario-toggle-button")
    scenario_button.innerText = f"Scenario: {SCENARIOS[runstate.state.scenario]['label']}"
    scenario_locked = (runstate.state.round_number != 1 or any(runstate.state.cumulative_built.values())) and not runstate.sandbox_active
    scenario_button.disabled = scenario_locked
    scenario_button.title = (
        "Starting scenario -- locked once you build anything or advance a round."
        if scenario_locked
        else (
            "Sandbox: click to cycle the scenario and start the practice grid over."
            if runstate.sandbox_active
            else "Click to cycle the starting scenario (only available before your first build or round)."
        )
    )

    document.getElementById("renewable-milestone-callout").hidden = not runstate.renewable_milestone_visible
    document.getElementById("retire-callout").hidden = not runstate.retire_callout_visible
    document.getElementById("maintain-callout").hidden = not runstate.maintain_callout_visible

    # TODO-C7: demand-response lever -- a fourth build/retire/maintain-
    # style action, but acting on demand growth instead of the fleet.
    dr_cost = runstate.state.demand_response_cost()
    dr_button = document.getElementById("demand-response-button")
    dr_button.innerText = f"Invest in Demand Response ({dr_cost:.0f})"
    dr_button.disabled = runstate.state.funds < dr_cost
    dr_button.title = (
        f"Permanently trims demand growth by {DEMAND_RESPONSE_REDUCTION_PER_LEVEL:g}/round "
        f"(floor {DEMAND_RESPONSE_MIN_GROWTH:g}/round). Each purchase costs more than the last."
    )
    document.getElementById("demand-response-level-display").innerText = (
        f"Demand response level: {runstate.state.demand_response_level}"
        if runstate.state.demand_response_level > 0
        else "Demand response: not yet invested"
    )

    # TODO-C19: policy lever -- offered periodically, opt-in.
    policy_banner = document.getElementById("policy-lever-banner")
    policy_banner.hidden = not runstate.state.policy_lever_available
    active_policy_el = document.getElementById("active-policy-display")
    if runstate.state.active_policy is None:
        active_policy_el.innerText = ""
        active_policy_el.hidden = True
    else:
        active_policy_el.hidden = False
        label = (
            "Carbon Pricing" if runstate.state.active_policy["type"] == "carbon_pricing" else "Renewable Subsidy"
        )
        effect = (
            f"fossil build costs +{(CARBON_PRICING_FOSSIL_COST_MULTIPLIER - 1) * 100:.0f}%"
            if runstate.state.active_policy["type"] == "carbon_pricing"
            else f"renewable build costs -{(1 - RENEWABLE_SUBSIDY_COST_MULTIPLIER) * 100:.0f}%"
        )
        active_policy_el.innerText = (
            f"Active policy: {label} -- {effect} ({runstate.state.active_policy['rounds_remaining']} round(s) left)."
        )

    _render_arbitrage_and_emergency()
    render_auto_advance()
    render_round_recap()
    render_difficulty_preset()
    render_run_setup_and_extras()
    update_career_panel()

    for plant_type in PLANT_TYPES:
        count = runstate.state.plant_counts[plant_type]
        cost = runstate.state.plant_cost(plant_type)
        document.getElementById(f"{plant_type}-count").innerText = str(count)
        name_el = document.getElementById(f"{plant_type}-name")
        name_el.innerText = f"{PLANT_ICON[plant_type]} {PLANT_LABEL[plant_type]}"
        for _, wear_css_class in AGE_WEAR_THRESHOLDS:
            name_el.classList.remove(wear_css_class)
        wear_css_class = runstate.state.wear_class(plant_type)
        if wear_css_class:
            name_el.classList.add(wear_css_class)

        # C10: the exact wear percentage next to the coarse wear-icon
        # state -- only meaningful once a unit is actually standing.
        wear_pct_el = document.getElementById(f"{plant_type}-wear-pct")
        wear_pct_el.innerText = (
            f"{WEAR_TIER_GLYPH[wear_css_class]} {runstate.state.wear_percent(plant_type)}% worn" if count > 0 else ""
        )
        wear_pct_el.title = wear_tooltip(plant_type) if count > 0 else ""

        # C19: a breakdown-risk badge once this type's own average age
        # has crossed the risk threshold, independent of whether it's
        # currently *the* oldest type (the one actually at risk this
        # round -- see breakdown_risk_probability()'s docstring).
        risk_badge = document.getElementById(f"{plant_type}-risk-badge")
        risk_probability = runstate.state.breakdown_risk_probability(plant_type) if count > 0 else 0.0
        risk_badge.hidden = risk_probability <= 0.0
        if not risk_badge.hidden:
            risk_badge.innerText = f"⚠ Aging risk ({risk_probability * 100:.0f}%)"

        build_button = document.getElementById(f"{plant_type}-build-button")
        build_button.innerText = f"Build ({cost:.0f})"
        build_button.disabled = runstate.state.funds < cost

        retire_button = document.getElementById(f"{plant_type}-retire-button")
        retire_button.disabled = count <= 0

        maintenance_cost = runstate.state.maintenance_cost(plant_type)
        maintain_button = document.getElementById(f"{plant_type}-maintain-button")
        maintain_button.innerText = f"Maintain ({maintenance_cost:.0f})"
        maintain_button.disabled = count <= 0 or runstate.state.funds < maintenance_cost

        # TODO-C23: keep the select's own displayed value in sync with
        # state (e.g. after a load_state() or a grid-size reset), same
        # reasoning as the difficulty/grid-size <select>s elsewhere in
        # this file -- disabled whenever there's no plant of this type to
        # schedule anything for, same gating as Maintain itself.
        schedule_select = document.getElementById(f"{plant_type}-maintenance-schedule-select")
        schedule_select.value = str(runstate.state.maintenance_schedule[plant_type])
        schedule_select.disabled = count <= 0

    # C7: plant-mix bar chart -- composition of *generation* capacity by
    # type. Battery has no row here (see GENERATION_TYPES' comment) --
    # it's storage, not part of "what's generating," so it has no
    # meaningful share of a generation-mix chart.
    for plant_type in GENERATION_TYPES:
        mix_pct = runstate.state.capacity_share(plant_type) * 100
        document.getElementById(f"{plant_type}-mix-bar").style.width = f"{mix_pct:.0f}%"
        document.getElementById(f"{plant_type}-mix-pct").innerText = f"{mix_pct:.0f}%"


def update_career_panel():
    toggle = document.getElementById("career-toggle-button")
    panel = document.getElementById("career-panel")
    toggle.innerText = "Hide Career" if runstate.career_open else f"🎖️ Career ({career_points_available()} pts)"
    panel.hidden = not runstate.career_open
    if not runstate.career_open:
        return
    stats, preview = career_panel_lines()
    document.getElementById("career-stats-display").innerText = stats
    document.getElementById("career-preview-display").innerText = preview
    document.getElementById("career-records-display").innerText = career_records_text()
    flash = document.getElementById("career-record-flash")
    flash.hidden = not runstate.last_finish_records
    flash.innerText = ("New record! " + "; ".join(runstate.last_finish_records) + ".") if runstate.last_finish_records else ""
    document.getElementById("career-next-perk-display").innerText = career_next_perk_text()
    finish = document.getElementById("career-finish-button")
    finish.disabled = runstate.sandbox_active or runstate.state.round_number - 1 < CAREER_MIN_ROUNDS
    document.getElementById("career-tree-summary").innerText = career_tree_summary_text()
    _render_career_tree()

    history = runstate.career["history"]
    list_el = document.getElementById("career-history-list")
    list_el.innerHTML = ""
    rows = career_history_rows(history)
    if not rows:
        empty = document.createElement("p")
        empty.className = "comparison-message"
        empty.innerText = "No finished runs yet. Finish a run and it is filed here."
        list_el.appendChild(empty)
    for row_text in rows:
        row = document.createElement("p")
        row.className = "career-history-row"
        row.innerText = row_text
        list_el.appendChild(row)
    document.getElementById("career-history-chart").innerHTML = career_history_charts_html(history)
    document.getElementById("career-lifetime-display").innerText = "\n".join(career_lifetime_lines())
    document.getElementById("career-heatmap").innerHTML = career_heatmap_html(history)
    render_career_whatif(history)
    document.getElementById("career-data-status").innerText = runstate.career_data_message


def _on_tree_buy(node_id, node=None):
    unlock_career_perk(str(node_id))
    render()


def _render_career_tree():
    """Draws (or updates) the shared skill-tree widget into #career-tree. Without the script (the
    tests, or a failed load) the tree is simply not drawn; the plain-text summary above it stays."""
    window = _js_window()
    widget = getattr(window, "NoyvjSkillTree", None) if window is not None else None
    container = document.getElementById("career-tree")
    if widget is None or container is None:
        return
    if runstate._career_view is None:
        if not _career_proxies:
            _career_proxies.append(create_proxy(_on_tree_buy))
        options = _to_js({
            "tree": CAREER_TREE, "owned": list(runstate.career["unlocked"]), "earned": runstate.career["points"],
            "refundNodes": False, "onBuy": _career_proxies[0],
        })
        if options is not None:
            runstate._career_view = widget.render(container, options)
        return
    update = _to_js({"owned": list(runstate.career["unlocked"]), "earned": runstate.career["points"]})
    if update is not None:
        runstate._career_view.update(update)
