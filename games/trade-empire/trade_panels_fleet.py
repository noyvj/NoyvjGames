"""Page renders for ships, colonies, needs strips, sparklines and the almanac."""

from js import document

import trade_runstate as runstate
from trade_blackout import blackout_has
from trade_charter import automation_cost, development_threshold
from trade_colony import (
    _system_label_for_colony, active_colony_ids, colony_needing, colony_producing, colony_states,
)
from trade_mapdraw import colony_map_label
from trade_market import (
    MAX_PRICE_MULTIPLIER, MIN_PRICE_MULTIPLIER, market_multiplier, need_history, price_memory,
)
from trade_research import IDLE_WARNING_TICKS
from trade_rules import (
    ALL_COLONIES, CONCESSION_COST, GOOD_LABEL, PURCHASABLE_SHIP_IDS, SELL_PRICE, SPECIALIZATION,
    TEMPERAMENTS, TEMPERAMENT_MARK,
)
from trade_ships import (
    COLONY_INVEST_UNITS, DEFAULT_ARCHETYPE, SHIP_PURCHASE_COST, VETERAN_ROUND_TRIPS, archetype_for,
    automation_slots_available, can_grant_concession, can_invest_in_colony, can_purchase_ship,
    colony_invest_cost_for,
)
from trade_weather import weather_almanac_note


def sell_summary(good, qty, profit, colony_id):
    colony_name = ALL_COLONIES[colony_id]["name"]
    return f"Sold {qty} {GOOD_LABEL[good]} at {colony_name} for {profit} credits."


def ship_status_text(ship):
    if ship.on_expedition:  # J-23
        return f"On an expedition away from the routes: back in {runstate.expedition['left']} tick(s)."
    if ship.in_transit:
        dest_name = ALL_COLONIES[ship.destination]["name"]
        prefix = "Automated — in transit" if ship.automated else "In transit"
        return f"{prefix} to {dest_name} — {ship.transit_ticks_remaining} tick(s) remaining."
    colony = ALL_COLONIES[ship.location]
    if ship.automated:
        return f"Automated — docked at {colony['name']}, running its route on its own."
    if ship.loaded:
        return f"Docked at {colony['name']}, loaded with {ship.cargo_qty} {GOOD_LABEL[ship.cargo_good]}. Choose a destination."
    base = f"Docked at {colony['name']}. Load {GOOD_LABEL[colony['produces']]} to prepare a run."
    if ship.idle_ticks >= IDLE_WARNING_TICKS:
        base += f" ⚠️ Idle for {ship.idle_ticks} ticks — consider loading it or automating this route."
    return base


def _render_unpurchased_ship(ship):
    """J6 — ship 5/6 before their one-time purchase: every normal control
    stays hidden, replaced by a single purchase button + status line."""
    document.getElementById(f"ship-{ship.id}-status").innerText = (
        f"Not yet purchased — {SHIP_PURCHASE_COST[ship.id]} credits to add it to the fleet."
    )
    document.getElementById(f"ship-{ship.id}-load-button").hidden = True
    document.getElementById(f"ship-{ship.id}-automate-button").hidden = True
    for colony_id in ALL_COLONIES:
        document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button").hidden = True

    archetype_select = document.getElementById(f"ship-{ship.id}-archetype-select")
    if archetype_select is not None:
        archetype_select.hidden = False
    purchase_button = document.getElementById(f"ship-{ship.id}-purchase-button")
    purchase_button.hidden = False
    purchase_button.innerText = f"Purchase Ship ({SHIP_PURCHASE_COST[ship.id]})"
    purchase_button.disabled = not can_purchase_ship(ship.id)


def render_ship(ship):
    label_text = ship.name
    if ship.archetype != DEFAULT_ARCHETYPE:
        label_text += f" ({archetype_for(ship)['label']})"
    if ship.purchased and ship.is_veteran:
        label_text += " ★ Veteran hauler"  # J14
    label_el = document.getElementById(f"ship-{ship.id}-label")
    label_el.innerText = label_text
    label_el.title = (
        f"{ship.round_trips} round trips on the same route (veteran at {VETERAN_ROUND_TRIPS})."
        if ship.purchased else ""
    )

    if ship.id in PURCHASABLE_SHIP_IDS:
        purchase_button = document.getElementById(f"ship-{ship.id}-purchase-button")
        if not ship.purchased:
            _render_unpurchased_ship(ship)
            return
        purchase_button.hidden = True
        archetype_select = document.getElementById(f"ship-{ship.id}-archetype-select")
        if archetype_select is not None:
            archetype_select.hidden = True

    status_el = document.getElementById(f"ship-{ship.id}-status")
    status_el.innerText = ship_status_text(ship)
    # J15 — a manual ship left idle and empty for a long stretch gets a
    # distinct status style, a nudge that's easy to miss in a wall of
    # otherwise-identical "docked, nothing loaded" panels.
    idle_warning = not ship.automated and ship.idle_ticks >= IDLE_WARNING_TICKS
    status_el.className = "ship-status ship-status--idle-warning" if idle_warning else "ship-status"

    load_button = document.getElementById(f"ship-{ship.id}-load-button")
    load_button.hidden = ship.automated
    load_button.disabled = ship.automated or not (ship.docked and not ship.loaded)

    reachable = active_colony_ids()
    for colony_id in ALL_COLONIES:
        depart_button = document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button")
        applicable = (
            ship.docked and ship.loaded and colony_id != ship.location and colony_id in reachable
        )
        depart_button.hidden = ship.automated or not applicable
        depart_button.disabled = ship.automated or not applicable

    automate_button = document.getElementById(f"ship-{ship.id}-automate-button")
    automate_button.hidden = False
    # J18 — automation is a one-time, permanent choice per ship.
    automate_button.title = (
        f"Automating costs {automation_cost()} credits and is permanent: "
        "there is no way to de-automate a ship afterward."
    )
    if ship.automated:
        automate_button.innerText = "Automated"
        automate_button.disabled = True
    else:
        automate_button.innerText = f"Automate ({automation_cost()})"
        automate_button.disabled = not automation_slots_available() or runstate.total_profit < automation_cost()


def render_colony(colony_id):
    colony = ALL_COLONIES[colony_id]
    state = colony_states[colony_id]
    need_text = (
        f"{colony['name']}: needs {GOOD_LABEL[colony['needs']]} — "
        f"{state.need_satisfaction * 100:.0f}% satisfied"
    )
    if state.is_developed():
        need_text += (
            f"; also needs {GOOD_LABEL[state.secondary_need()]} — "
            f"{state.secondary_need_satisfaction * 100:.0f}% satisfied"
        )
    need_text += f" (output x{state.output_multiplier():.2f})"
    document.getElementById(f"colony-{colony_id}-need-display").innerText = need_text
    document.getElementById(f"colony-{colony_id}-need-bar").style.width = (
        f"{state.need_satisfaction * 100:.0f}%"
    )
    # J14 — a need-satisfaction-over-time sparkline alongside the meter.
    document.getElementById(f"colony-{colony_id}-need-sparkline").innerHTML = _trend_sparkline_svg(
        need_history.get(colony_id, []), "need-sparkline"
    ) if blackout_has("feed") else ""
    # J24 — a plain "needs met" average alongside the graph.
    hist = need_history.get(colony_id, [])
    if hist and blackout_has("feed"):
        avg_pct = sum(hist) / len(hist) * 100
        document.getElementById(f"colony-{colony_id}-need-sparkline").innerHTML += (
            f'<span class="sparkline-pct" title="Average need satisfaction over the last '
            f'{len(hist)} ticks">avg {avg_pct:.0f}%</span>'
        )

    dev_el = document.getElementById(f"colony-{colony_id}-development-display")
    if state.is_developed():
        spec = SPECIALIZATION[colony_id]
        dev_el.innerText = f"Development: Level 2 — {spec['name']} ({spec['description']})"
    else:
        dev_el.innerText = (
            f"Development: Level 1 ({state.cumulative_delivered:.0f}/{development_threshold():.0f} "
            f"{GOOD_LABEL[colony['needs']]} delivered to develop further)"
        )
    demand_el = document.getElementById(f"colony-{colony_id}-demand-display")
    concede_button = document.getElementById(f"colony-{colony_id}-concede-button")
    if demand_el is not None and concede_button is not None:
        demanding = state.has_demand()
        demand_el.hidden = not demanding
        concede_button.hidden = not demanding
        if demanding:
            demand_el.innerText = (
                f"{colony['name']} feels neglected and asks for a concession: {CONCESSION_COST} credits "
                f"to restore {int(state.concession_boost() * 100)}% satisfaction "
                f"({state.demand_ticks_left} tick(s) left; ignoring it costs nothing)."
            )
            concede_button.innerText = f"Grant concession ({CONCESSION_COST})"
            concede_button.disabled = not can_grant_concession(colony_id)
    invest_button = document.getElementById(f"colony-{colony_id}-invest-button")
    if invest_button is not None:
        invest_button.hidden = state.is_developed()
        invest_button.innerText = f"Invest ({colony_invest_cost_for(colony_id)})"
        invest_button.disabled = not can_invest_in_colony(colony_id)
        invest_button.title = (
            f"Spend {colony_invest_cost_for(colony_id)} credits to add {COLONY_INVEST_UNITS} units of development progress "
            f"({COLONY_INVEST_UNITS / development_threshold() * 100:.0f}% of Level 2)."
        )
    mood_el = document.getElementById(f"colony-{colony_id}-temperament")
    if mood_el is not None:
        mood_el.innerText = temperament_text(colony_id)


def temperament_text(colony_id):
    """J-25/J-26 -- the colony panel's one-line explanation of its mood."""
    state = colony_states[colony_id]
    mood = TEMPERAMENTS[state.temperament()]
    return (
        f"Mood: {TEMPERAMENT_MARK[mood['glyph']]} {mood['label']} ({mood['glyph']} on the map): {mood['why']}. "
        f"History: {state.cumulative_delivered:.0f} delivered, {state.concessions_granted} concession(s) granted, "
        f"{state.lapsed_demands()} demand(s) unanswered."
    )


def render_needs_strip():
    """Mobile-dock companion to #colonies-panel (see style.css) -- one
    compact chip per colony with just enough to pick a depart
    destination without scrolling back up to the full colonies panel:
    which good it needs and how satisfied that need currently is. A
    colony's chip stays hidden until its ColonyState exists, the same
    gate render()'s main loop already uses for colony_states."""
    for colony_id in ALL_COLONIES:
        chip = document.getElementById(f"mobile-needs-strip-{colony_id}")
        state = colony_states.get(colony_id)
        chip.hidden = state is None
        if state is None:
            continue
        colony = ALL_COLONIES[colony_id]
        chip.innerText = (
            f"{colony_map_label(colony_id)}: needs {GOOD_LABEL[colony['needs']]} "
            f"{state.need_satisfaction * 100:.0f}%"
        )


SPARKLINE_WIDTH = 60
SPARKLINE_HEIGHT = 18


def _trend_sparkline_svg(history, css_class, now_label=None, ghost=None, ghost_label=None):
    """J12/J14 — an unlabeled inline-SVG polyline over a short rolling
    history; the point is the shape of the trend, not any exact value.
    Values are expected roughly in 0..1 (market multiplier, need
    satisfaction) so a fixed height mapping is enough -- no separate
    axis scaling needed. J-4: `ghost` (a 0..1 value) adds a dashed
    horizontal "price memory" line at that level."""
    if len(history) < 2:
        return ""
    n = len(history)
    points = []
    for i, value in enumerate(history):
        x = (i / (n - 1)) * SPARKLINE_WIDTH
        y = SPARKLINE_HEIGHT - max(0.0, min(1.0, value)) * SPARKLINE_HEIGHT
        points.append(f"{x:.1f},{y:.1f}")
    # J4 — an explicit, labeled marker on the most recent point.
    marker = ""
    if now_label:
        last_x, last_y = points[-1].split(",")
        marker = (
            f'<circle cx="{last_x}" cy="{last_y}" r="2" class="sparkline-now">'
            f"<title>{now_label}</title></circle>"
        )
    ghost_line = ""
    if ghost is not None:
        gy = SPARKLINE_HEIGHT - max(0.0, min(1.0, ghost)) * SPARKLINE_HEIGHT
        ghost_line = (
            f'<line x1="0" y1="{gy:.1f}" x2="{SPARKLINE_WIDTH}" y2="{gy:.1f}" class="sparkline-ghost" '
            f'stroke-dasharray="3 2"><title>{ghost_label or "Price before your last stockpile trade"}</title></line>'
        )
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="{css_class}" '
        f'aria-hidden="{"false" if now_label else "true"}">{ghost_line}<polyline points="{" ".join(points)}" />{marker}</svg>'
    )


def price_memory_text(good):
    """J-4 -- the text twin of the ghost line (the line is dashed, never colour only)."""
    if good not in price_memory:
        return ""
    return (
        f"dashed line: {price_memory[good] * 100:.0f}% of baseline before your last stockpile trade "
        f"(now {market_multiplier[good] * 100:.0f}%)"
    )


def almanac_rows():
    rows = []
    reachable = set(active_colony_ids())
    for good, base in SELL_PRICE.items():
        producer = colony_producing(good)
        consumer = colony_needing(good)
        if producer not in reachable:
            continue
        rows.append({
            "good": GOOD_LABEL[good],
            "base": base,
            "low": round(base * MIN_PRICE_MULTIPLIER, 1),
            "high": round(base * MAX_PRICE_MULTIPLIER, 1),
            "made_by": ALL_COLONIES[producer]["name"],
            "needed_by": ALL_COLONIES[consumer]["name"] if consumer else "nobody",
            "system": _system_label_for_colony(producer),
        })
    return rows


def render_almanac():
    body = document.getElementById("almanac-body")
    if body is None:
        return
    lines = [
        "<table class=\"almanac-table\"><thead><tr><th>Good</th><th>Base</th>"
        "<th>Typical range</th><th>Made by</th><th>Needed by</th></tr></thead><tbody>"
    ]
    for row in almanac_rows():
        lines.append(
            f"<tr><td>{row['good']}</td><td>{row['base']}</td>"
            f"<td>{row['low']:g}\u2013{row['high']:g}</td>"
            f"<td>{row['made_by']} <span class=\"almanac-system\">({row['system']})</span></td>"
            f"<td>{row['needed_by']}</td></tr>"
        )
    lines.append("</tbody></table>")
    lines.append(weather_almanac_note())
    body.innerHTML = "".join(lines)
