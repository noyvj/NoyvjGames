"""Small views: demand-growth arrow, wear tooltip, render_trend, plant-mix and gauge tables, chart theme.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import (
    AGE_BREAKDOWN_RATE, AGE_GRACE_PERIOD, EMISSIONS_FACTOR, EMISSIONS_METER_MAX, GENERATION_TYPES,
    MAINTENANCE_AGE_REDUCTION, MAX_AGE_BREAKDOWN_PROBABILITY, PLANT_CAPACITY, PLANT_LABEL,
    STEEP_DEMAND_GROWTH_MULTIPLIER, WEAR_PERCENT_REFERENCE_AGE,
)
from grid_trend import (
    DEFAULT_TREND_LINES, TREND_LINE_KEYS, TREND_LINE_LABEL, ghost_delta_text, ghost_record, trend_description,
    trend_graph_svg, trend_series, trend_table_html, visible_trend_lines,
)


def demand_growth_arrow():
    """C20 (extended by TODO-C7): demand's per-round growth against the
    standard pace -- up when net growth is faster than standard, flat
    when unchanged, and (new) down once demand-response investment has
    pulled net growth below standard, regardless of the Steeper Demand
    Growth toggle."""
    growth = runstate.state.demand_growth_this_round()
    standard = runstate.state.base_demand_growth
    if growth > standard:
        return "\u25B2"
    if growth < standard:
        return "\u25BC"
    return "\u25AC"


def demand_growth_title():
    growth = runstate.state.demand_growth_this_round()
    if runstate.state.demand_response_level > 0:
        baseline = runstate.state.base_demand_growth * (
            STEEP_DEMAND_GROWTH_MULTIPLIER if runstate.state.steeper_demand_growth_enabled else 1
        )
        return (
            f"Demand is rising +{growth:.1f} per round -- demand-response investment "
            f"(level {runstate.state.demand_response_level}) has trimmed it down from the "
            f"otherwise-{baseline:.0f}-per-round pace."
        )
    if runstate.state.steeper_demand_growth_enabled:
        return f"Demand is rising +{growth:.0f} per round -- faster than the standard +{runstate.state.base_demand_growth:g} (Steeper Demand Growth is on)."
    return f"Demand is rising at the standard +{runstate.state.base_demand_growth:g} per round."


def wear_tooltip(plant_type):
    """C4: what the wear percentage means numerically."""
    age = runstate.state.plant_age[plant_type]
    return (
        f"Average fleet age {age:.1f} rounds. Wear % = age / {WEAR_PERCENT_REFERENCE_AGE} rounds (100% is the "
        f"top wear tier). Breakdown risk starts past {AGE_GRACE_PERIOD} rounds: +{AGE_BREAKDOWN_RATE * 100:.0f}% "
        f"per extra round, capped at {MAX_AGE_BREAKDOWN_PROBABILITY * 100:.0f}%. Maintain takes "
        f"{MAINTENANCE_AGE_REDUCTION} rounds off the average age."
    )


TREND_CHECKBOX_PREFS = tuple(
    [(f"trend-show-{key}", f"trend_{key}") for key in TREND_LINE_KEYS]
    + [("trend-show-ghost", "trend_ghost"), ("chart-table-view", "table_view")]
)
TREND_DEFAULT_MESSAGE = (
    "Your emissions (red) vs. a global-average-fossil-mix benchmark (dashed grey) vs. average renewable cost "
    "(blue, fine dashes) over time."
)


def render_trend():
    """C-12 / C-19 / GC-9: the trend graph (or its table), the line checkboxes and the ghost line."""
    for element_id, pref_key in TREND_CHECKBOX_PREFS:
        document.getElementById(element_id).checked = runstate.prefs[pref_key]
    visible = visible_trend_lines()
    ghost = ghost_record() if runstate.prefs["trend_ghost"] else None
    svg = trend_graph_svg(
        runstate.state.emissions_history,
        runstate.state.avg_renewable_cost_history,
        runstate.state.global_reference_emissions_history,
        runstate.state.clean_fraction_log,
        visible=visible,
        funds_history=runstate.state.funds_history,
        demand_history=runstate.state.demand_history,
        ghost=ghost,
    )
    series = trend_series(
        runstate.state.emissions_history, runstate.state.avg_renewable_cost_history, runstate.state.global_reference_emissions_history,
        runstate.state.clean_fraction_log, runstate.state.funds_history, runstate.state.demand_history,
    )
    graph_el = document.getElementById("trend-graph")
    message_el = document.getElementById("trend-graph-message")
    if not svg:
        graph_el.innerHTML = ""
        message_el.innerText = "Not enough rounds yet to show an emissions/cost trend."
    elif runstate.prefs["table_view"]:
        graph_el.innerHTML = trend_table_html(series, visible, runstate.state.clean_fraction_log, ghost)
        message_el.innerText = trend_description(series, visible)
    else:
        graph_el.innerHTML = svg
        if not visible:
            message_el.innerText = "No lines are switched on. Use the checkboxes above to show some."
        elif visible == DEFAULT_TREND_LINES:
            message_el.innerText = TREND_DEFAULT_MESSAGE
        else:
            shown = ", ".join(TREND_LINE_LABEL[k].lower() for k in TREND_LINE_KEYS if k in visible)
            message_el.innerText = f"Showing {shown} over time."
    note_el = document.getElementById("trend-ghost-note")
    note_el.hidden = not runstate.prefs["trend_ghost"]
    if runstate.prefs["trend_ghost"]:
        text = ghost_delta_text(runstate.state.clean_fraction_log, runstate.state.funds_history, ghost)
        if ghost and not ({"clean", "funds"} & visible):
            text += " Switch on Clean share or Funds to see the ghost line."
        note_el.innerText = text


def mix_table_html():
    """C-19: the plant-mix chart as a plain table (units, share of capacity, of revenue, of emissions)."""
    total_capacity = runstate.state.total_capacity()
    emissions_total = sum(
        runstate.state.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t] for t in GENERATION_TYPES
    )
    rows = []
    for plant_type in GENERATION_TYPES:
        share = runstate.state.capacity_share(plant_type) * 100
        emissions = runstate.state.plant_counts[plant_type] * PLANT_CAPACITY[plant_type] * EMISSIONS_FACTOR[plant_type]
        emission_share = (emissions / emissions_total * 100) if emissions_total > 0 else 0.0
        rows.append(
            f'<tr><th scope="row">{PLANT_LABEL[plant_type]}</th><td>{runstate.state.plant_counts[plant_type]}</td>'
            f"<td>{share:.0f}%</td><td>{share:.0f}%</td><td>{emission_share:.0f}%</td></tr>"
        )
    note = (
        "No generation on the grid yet." if total_capacity <= 0
        else f"Revenue share equals capacity share: every unit of output sold earns the same. Total capacity {total_capacity}."
    )
    return (
        f'<table class="chart-table"><caption>Plant mix. {note}</caption><thead><tr>'
        '<th scope="col">Plant</th><th scope="col">Units</th><th scope="col">Share of capacity</th>'
        '<th scope="col">Share of revenue</th><th scope="col">Share of emissions</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def gauge_table_html():
    """C-19: the meters (emissions, clean-grid score, disruption risk, fossil share, supply against demand) as
    a plain table with the same numbers the bars draw."""
    emissions_pct = min(1.0, runstate.state.emissions / EMISSIONS_METER_MAX) * 100
    capacity = runstate.state.total_capacity()
    cover = (capacity / runstate.state.demand * 100) if runstate.state.demand > 0 else 0.0
    rows = [
        ("Emissions meter", f"{runstate.state.emissions:.0f} of {EMISSIONS_METER_MAX:.0f}", f"{emissions_pct:.0f}% full"),
        ("Sustained clean-grid score", f"{runstate.state.score():.0f} of 100", f"{runstate.state.score():.0f}% full"),
        ("Disruption risk next round", f"{runstate.state.disruption_probability() * 100:.0f}%", "chance"),
        ("Fossil share of grid", f"{runstate.state.fossil_share() * 100:.0f}%", "of capacity"),
        ("Supply against demand", f"{capacity} of {runstate.state.demand:.0f}", f"{cover:.0f}% covered"),
    ]
    body = "".join(f'<tr><th scope="row">{a}</th><td>{b}</td><td>{c}</td></tr>' for a, b, c in rows)
    return (
        '<table class="chart-table"><caption>The gauges as numbers.</caption><thead><tr><th scope="col">Gauge</th>'
        '<th scope="col">Value</th><th scope="col">Reading</th></tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def render_chart_theme():
    """C-28: the chosen chart theme goes on the trend graph, its checkboxes and the plant-mix section; the look
    itself is all in style.css (attribute selectors), so nothing here touches a number."""
    theme = runstate.prefs["chart_theme"]
    for element_id in ("trend-graph", "trend-controls", "plant-mix"):
        document.getElementById(element_id).dataset.chartTheme = theme
    document.getElementById("pref-chart-theme").value = theme


def render_unlock_flash_setting():
    document.getElementById("pref-unlock-flash").checked = runstate.prefs["unlock_flash"]


def render_chart_tables():
    """C-19: with 'Show charts as tables' on, the plant-mix bars and the gauges also get a plain table."""
    on = runstate.prefs["table_view"]
    mix_table = document.getElementById("mix-table")
    mix_table.hidden = not on
    mix_table.innerHTML = mix_table_html() if on else ""
    for plant_type in GENERATION_TYPES:
        document.getElementById(f"{plant_type}-mix-row").hidden = on
    gauge_table = document.getElementById("gauge-table")
    gauge_table.hidden = not on
    gauge_table.innerHTML = gauge_table_html() if on else ""


BENCH_OHMS_PER_KM = 0.05


def line_loss(voltage_kv, current_a, distance_km):
    """Power line bench: calculate transmission loss for a given voltage, current, and distance."""
    if voltage_kv <= 0 or current_a <= 0:
        return {"sent_mw": 0.0, "loss_mw": 0.0, "percent": 0.0}
    sent_mw = voltage_kv * current_a / 1000
    loss_mw = current_a ** 2 * BENCH_OHMS_PER_KM * max(0, distance_km) / 1e6
    percent = loss_mw / sent_mw * 100
    return {"sent_mw": sent_mw, "loss_mw": loss_mw, "percent": percent}
