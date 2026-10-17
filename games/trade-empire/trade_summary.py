"""The summary panel: trends, throughput, colony overview, route profitability, share result."""

import json

from js import document

import trade_runstate as runstate
from trade_achievements import ACHIEVEMENTS, achievement_ids_earned
from trade_charter import charter_summary_text
from trade_colony import colony_needing, colony_producing, colony_states
from trade_founding import legacy_summary_text
from trade_market import good_profit_recent, good_profit_total, good_trip_count
from trade_research import IDLE_WARNING_TICKS, RESEARCH_NODES, max_automated_ships
from trade_rules import ALL_COLONIES, GOOD_LABEL
from trade_ships import DEFAULT_TREND_EPSILON, UNDERPERFORM_FRACTION, automated_ship_count, ships


# ===========================================================================
# J9/J11 — an on-demand session summary, following the same toggle+panel
# idiom as the achievements panel (built, not open, by default; only
# populated when open; kept live across render() while open). J11's per-
# route profitability rides along here as the summary's second half,
# rather than a separate panel of its own -- colony_producing()/
# colony_needing() already make "route" and "good" the same concept in
# this game, so listing every good's cumulative sale profit *is* the
# per-route readout.
# ===========================================================================


def on_toggle_summary(event=None):
    runstate.summary_open = not runstate.summary_open
    update_summary_display()


def route_trend_arrow(good):
    """J2 — ▲ improving / ▼ declining / ▶ steady, comparing the newer half
    of the last few sales on this good against the older half. Needs at
    least 4 sales to say anything."""
    recent = good_profit_recent.get(good, [])
    if len(recent) < 4:
        return ""
    half = len(recent) // 2
    older = sum(recent[:half]) / half
    newer = sum(recent[half:]) / (len(recent) - half)
    if older <= 0:
        return ""
    change = (newer - older) / older
    if change > DEFAULT_TREND_EPSILON:
        return "▲"
    if change < -DEFAULT_TREND_EPSILON:
        return "▼"
    return "▶"


def fleet_efficiency_lines():
    """J25 — which purchased ships are earning well below the fleet
    average. Empty until at least two ships have earned something."""
    earners = [sh for sh in ships.values() if sh.purchased]
    total = sum(sh.total_earned for sh in earners)
    if len(earners) < 2 or total <= 0:
        return []
    avg = total / len(earners)
    lines = []
    for sh in earners:
        if sh.total_earned < avg * UNDERPERFORM_FRACTION:
            hint = "idle" if sh.idle_ticks >= IDLE_WARNING_TICKS else "consider automating or rerouting"
            lines.append(f"{sh.name}: {sh.total_earned:,} credits earned (fleet average {avg:,.0f}) — {hint}")
    return lines


THROUGHPUT_WINDOW = 100  # J-6 -- throughput is quoted per this many ticks


def ship_throughput(ship):
    """J-6 -- units this ship has delivered per THROUGHPUT_WINDOW ticks in the
    fleet (None until it has been in the fleet for a tick)."""
    if not ship.purchased or ship.ticks_owned <= 0:
        return None
    return ship.units_moved / ship.ticks_owned * THROUGHPUT_WINDOW


def route_throughput(good):
    """J-6 -- units of `good` moved per ship per THROUGHPUT_WINDOW ticks,
    measured over the ships that have hauled it (None if none has)."""
    haulers = [sh for sh in ships.values() if sh.units_by_good.get(good, 0) > 0 and sh.ticks_owned > 0]
    if not haulers:
        return None
    units = sum(sh.units_by_good[good] for sh in haulers)
    return units / sum(sh.ticks_owned for sh in haulers) * THROUGHPUT_WINDOW


def fleet_throughput():
    """Average per-ship throughput across the purchased ships that have run."""
    rates = [ship_throughput(sh) for sh in ships.values()]
    rates = [r for r in rates if r is not None]
    return sum(rates) / len(rates) if rates else None


def throughput_lines():
    lines = []
    for ship in ships.values():
        rate = ship_throughput(ship)
        if rate is not None and ship.units_moved > 0:
            lines.append(
                f"{ship.name}: {rate:.1f} units per {THROUGHPUT_WINDOW} ticks "
                f"({ship.units_moved:,} units over {ship.ticks_owned:,} ticks)"
            )
    return lines


def throughput_text():
    avg = fleet_throughput()
    if avg is None or not any(sh.units_moved for sh in ships.values()):
        return f"Throughput: no deliveries yet (units moved per ship per {THROUGHPUT_WINDOW} ticks)."
    return f"Throughput: {avg:.1f} units per ship per {THROUGHPUT_WINDOW} ticks across the fleet."


def colony_overview_lines():
    """J13 — every active colony's need/supply state on one screen."""
    lines = []
    for colony_id, state in colony_states.items():
        colony = ALL_COLONIES[colony_id]
        lines.append(
            f"{colony['name']}: {GOOD_LABEL[colony['needs']]} {state.need_satisfaction * 100:.0f}% "
            f"met, {GOOD_LABEL[colony['produces']]} x{state.output_multiplier():.2f} output"
            f"{' (developed)' if state.is_developed() else ''}"
        )
    return lines


def _route_profitability_lines():
    lines = []
    for good, total in good_profit_total.items():
        if total <= 0:
            continue
        producer = colony_producing(good)
        consumer = colony_needing(good)
        producer_name = ALL_COLONIES[producer]["name"] if producer else "?"
        consumer_name = ALL_COLONIES[consumer]["name"] if consumer else "?"
        arrow = route_trend_arrow(good)
        suffix = f" {arrow}" if arrow else ""
        trips = good_trip_count.get(good, 0)
        per_trip = f", avg {total // trips:,}/trip over {trips} trips" if trips > 0 else ""
        rate = route_throughput(good)
        per_ship = f", {rate:.1f} units/ship/{THROUGHPUT_WINDOW} ticks" if rate is not None else ""
        lines.append(f"{GOOD_LABEL[good]} ({producer_name} → {consumer_name}): {total:,} credits{per_trip}{per_ship}{suffix}")
    return lines


def _detach_copy_result_holder(panel):
    """Z-20: empties the summary panel but keeps the shared "Copy result" button's container (and so
    its listener and its "Copied" message) alive, returning it with whether it held keyboard focus."""
    holder = document.getElementById("summary-copy-result")
    focused = False
    try:
        focused = holder is not None and bool(holder.contains(document.activeElement))
    except Exception:  # noqa: BLE001 -- no focus API (tests)
        pass
    panel.innerHTML = ""
    return holder, focused


def _reattach_copy_result_holder(panel, held):
    holder, focused = held
    if holder is None:
        return
    panel.appendChild(holder)
    if focused:
        try:
            holder.querySelector("button").focus()
        except Exception:  # noqa: BLE001
            pass


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide): total profit, how far the empire got
    (colonies developed, ships) and whether the full-scale endgame was reached."""
    developed = sum(1 for state in colony_states.values() if state.is_developed())
    ships_owned = sum(1 for ship in ships.values() if ship.purchased)
    stats = [
        {"n": developed, "one": "colony developed", "many": "colonies developed"},
        {"n": ships_owned, "one": "ship", "many": "ships"},
    ]
    if runstate.endgame_reached:
        stats.append("endgame reached")
    return json.dumps({"game": "Trade Empire", "score": runstate.total_profit, "unit": "credits profit", "stats": stats})


def update_summary_display():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Summary" if runstate.summary_open else "📊 Summary"
    panel.hidden = not runstate.summary_open
    if not runstate.summary_open:
        return

    developed = sum(1 for state in colony_states.values() if state.is_developed())
    ships_owned = sum(1 for ship in ships.values() if ship.purchased)
    overview_lines = [
        f"Total profit: {runstate.total_profit:,} credits (peak {runstate.max_profit_ever:,})",
        f"Sales completed: {runstate.total_sales_count}",
        f"Ships owned: {ships_owned}/{len(ships)}",
        f"Ships automated: {automated_ship_count()}/{max_automated_ships()}",
        f"Research unlocked: {len(runstate.unlocked_research)}/{len(RESEARCH_NODES)}",
        f"Colonies developed: {developed}/{len(colony_states)}",
        f"Achievements: {len(achievement_ids_earned())}/{len(ACHIEVEMENTS)}",
        "Status: full-scale endgame reached" if runstate.endgame_reached else "Status: still building",
        legacy_summary_text(),
        charter_summary_text(),
    ]

    holder = _detach_copy_result_holder(panel)
    for line in overview_lines:
        p = document.createElement("p")
        p.className = "summary-line"
        p.innerText = line
        panel.appendChild(p)
    _reattach_copy_result_holder(panel, holder)

    route_heading = document.createElement("p")
    route_heading.className = "panel-label summary-route-heading"
    route_heading.innerText = "Route profitability"
    panel.appendChild(route_heading)

    route_lines = _route_profitability_lines()
    if not route_lines:
        empty = document.createElement("p")
        empty.className = "summary-line"
        empty.innerText = "No completed sales yet."
        panel.appendChild(empty)
    for line in route_lines:
        p = document.createElement("p")
        p.className = "summary-line"
        p.innerText = line
        panel.appendChild(p)

    for heading, lines, empty_text in (
        (f"Throughput per ship (units per {THROUGHPUT_WINDOW} ticks)", throughput_lines(), "No deliveries yet."),
        ("Fleet efficiency", fleet_efficiency_lines(), "No underperforming ships."),
        ("Galaxy overview", colony_overview_lines(), "No colonies yet."),
    ):
        h = document.createElement("p")
        h.className = "panel-label summary-route-heading"
        h.innerText = heading
        panel.appendChild(h)
        for line in lines or [empty_text]:
            p = document.createElement("p")
            p.className = "summary-line"
            p.innerText = line
            panel.appendChild(p)
