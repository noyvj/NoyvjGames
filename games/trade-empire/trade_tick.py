"""tick(): one second of game time, the sale spark burst and the tick loop starter."""

from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_blackout import blackout_note_endgame
from trade_cartel import cartel_tick
from trade_charter import (
    LAB_AUTOMATION_RESEARCH_MULTIPLIER, LEDGER_MAX, background_revenue_this_tick, charter_perk,
    ledger_record_sale,
)
from trade_colony import colony_states
from trade_crew import captain_note_veterans, run_automation
from trade_crises import crisis_tick
from trade_exchange import exchange_tick
from trade_expedition import expedition_tick
from trade_founding import endgame_criteria_met
from trade_ghost import _ghost_record_tick
from trade_guild import guild_record_delivery, guild_tick
from trade_mapdraw import age_dock_pulses
from trade_market import (
    INSURANCE_PREMIUM_PER_TICK, TREND_HISTORY_MAX_POINTS, apply_market_sale, good_profit_recent,
    good_profit_total, good_trip_count, market_multiplier, need_history, price_history, recover_market,
)
from trade_meridian import meridian_tick
from trade_panels_fleet import sell_summary
from trade_renderer import render
from trade_research import RESEARCH_PER_TICK
from trade_rules import ALL_COLONIES, TICK_INTERVAL_MS
from trade_ships import ROUTE_TREND_WINDOW, SALE_LOG_MAX_ENTRIES, ships, trade_post_income_per_tick
from trade_uikit import _effects_on, show_notice_toast
from trade_weather import weather_tick


# J22 — a small decorative particle/spark burst on a "high-value" sale.
# Purely cosmetic: tick() below only calls this *after* total_profit has
# already been updated and the sale logged, so it can never change or
# delay the actual sale numbers.
#
# Threshold reasoning: a home-system sale (Ore/Grain/Machinery/Water/
# Energy, base prices 5-10) tops out around 180 credits even at full
# specialization + full development, *without* the Hauler Refit research
# (Milestone 10's Forge World bonus, the biggest home-system output
# bonus: 18 units x 10 credits/unit for Machinery). Reaching 200+ takes
# genuine progress -- either that Hauler Refit unlock, a well-developed
# colony, or selling one of the pricier Kepler/Rift-tier goods (Isotopes,
# Crystal, Antimatter) -- so it reliably skips the very first, ordinary
# sales a new player makes, without being so high it's a once-a-
# playthrough rarity either.
SALE_SPARK_THRESHOLD = 200
SALE_SPARK_COUNT = 6
SALE_SPARK_DURATION_MS = 700


def _spark_burst_high_value_sale():
    """J22: bursts a handful of small spark elements out of the profit
    display, then removes them once their one-shot CSS animation
    (te-sale-spark in style.css) finishes. Same create/setTimeout+
    create_proxy/remove-after-timeout shape as
    _flash_personal_best_badge()-style one-shot effects elsewhere on the
    hub -- this one creates transient elements instead of toggling a
    class on a persistent one, since a burst needs several independently
    positioned dots rather than one badge.

    Appends into #sale-spark-container, a dedicated sibling of
    #profit-display-text inside #profit-display -- NOT into
    #profit-display-text itself, since render() overwrites that span's
    innerText every tick and would wipe the sparks out before they ever
    got a frame to paint."""
    container = document.getElementById("sale-spark-container")
    if container is None or not _effects_on():
        return
    sparks = []
    for i in range(SALE_SPARK_COUNT):
        spark = document.createElement("span")
        spark.className = f"sale-spark sale-spark-{i}"
        container.appendChild(spark)
        sparks.append(spark)

    def _cleanup():
        for spark in sparks:
            spark.remove()

    setTimeout(create_proxy(_cleanup), SALE_SPARK_DURATION_MS)


def tick(event=None):
    if runstate.chain_active is not None:  # J-5: the real corporation is set aside and the stand-in does not run
        render()
        return
    runstate.research_points += RESEARCH_PER_TICK * (LAB_AUTOMATION_RESEARCH_MULTIPLIER if charter_perk("lab_automation") else 1.0)
    if runstate.seasonal_demand_enabled:
        runstate.season_ticks += 1
    weather_tick()
    meridian_tick()
    cartel_tick()
    expedition_tick()
    for ship in ships.values():
        result = ship.advance_transit()
        if result is not None:
            good, qty, profit = result
            if qty == 0:
                # J11 -- a disrupted trip: only an insurance payout (if any)
                # counts; no sale, no market impact, no delivery.
                runstate.total_profit += profit
                note = f" Insurance paid {profit} credits." if profit else ""
                show_notice_toast(f"\u26a0\ufe0f {ship.name}'s cargo was lost on the route.{note}")
                continue
            runstate.total_profit += profit
            runstate.total_sales_count += 1
            runstate.goods_sold_ever.add(good)
            good_profit_total[good] = good_profit_total.get(good, 0) + profit
            good_trip_count[good] = good_trip_count.get(good, 0) + 1
            recent = good_profit_recent.setdefault(good, [])
            recent.append(profit)
            del recent[:-2 * ROUTE_TREND_WINDOW]
            runstate.sale_log.append(sell_summary(good, qty, profit, ship.location))
            del runstate.sale_log[:-SALE_LOG_MAX_ENTRIES]
            guild_record_delivery(good, ship.location, qty)
            ledger_record_sale(qty, ship.route_key)
            apply_market_sale(good, qty)
            if profit >= SALE_SPARK_THRESHOLD:
                _spark_burst_high_value_sale()
            # J8 — a lightweight arrival toast, manual ships only: once a
            # ship is automated the player isn't meant to be watching
            # every individual cycle any more, so toasting every one of
            # an automated ship's (much more frequent) arrivals would be
            # the opposite of "lightweight."
            if not ship.automated:
                show_notice_toast(
                    f"🚚 {ship.name} arrived at {ALL_COLONIES[ship.location]['name']}."
                )
    age_dock_pulses()
    guild_tick()
    if runstate.route_hazards_enabled and runstate.route_insurance_enabled:
        for ship in ships.values():
            if ship.in_transit and runstate.total_profit >= INSURANCE_PREMIUM_PER_TICK:
                runstate.total_profit -= INSURANCE_PREMIUM_PER_TICK
                runstate.premiums_paid += INSURANCE_PREMIUM_PER_TICK
    run_automation()
    for colony_state in colony_states.values():
        colony_state.decay()
        colony_state.update_loyalty()
    recover_market()
    exchange_tick()  # J-27
    runstate.total_profit += trade_post_income_per_tick()

    # J15 — idle-ticks bookkeeping: counts up only while a ship is
    # purchased, manual, docked, and empty; anything else (in transit,
    # loaded, automated, unpurchased) resets it to zero.
    for ship in ships.values():
        if ship.purchased and not ship.automated and ship.docked and not ship.loaded:
            ship.idle_ticks += 1
        else:
            ship.idle_ticks = 0
        if ship.purchased:
            ship.ticks_owned = min(LEDGER_MAX, ship.ticks_owned + 1)  # J-6
    captain_note_veterans()  # J-7

    # J12/J14 — a short rolling history per good/colony, just long enough
    # for a small trend sparkline to read as a shape rather than noise.
    for good in market_multiplier:
        history = price_history.setdefault(good, [])
        history.append(market_multiplier[good])
        del history[:-TREND_HISTORY_MAX_POINTS]
    for colony_id, colony_state in colony_states.items():
        history = need_history.setdefault(colony_id, [])
        history.append(colony_state.need_satisfaction)
        del history[:-TREND_HISTORY_MAX_POINTS]

    if not runstate.endgame_reached and endgame_criteria_met():
        runstate.endgame_reached = True
        blackout_note_endgame()  # J-30
    if runstate.endgame_reached:
        runstate.ticks_since_endgame += 1
        runstate.total_profit += background_revenue_this_tick()

    runstate.max_profit_ever = max(runstate.max_profit_ever, runstate.total_profit)
    _ghost_record_tick()  # Z-3e5

    crisis_tick()  # J-9
    render()


def _start_tick_loop():
    """W-2: hands `tick` to shared/time-controls.js (pause and 1x/2x/4x) when the
    page has it, otherwise falls back to the plain setInterval this game always
    used (fake-js test environments and any page without the shared script).
    Either way the tick itself is untouched: the controller only changes how
    often it is called, and not at all while paused or while the tab is hidden
    (shared/pause-hidden.js). Returns "shared" or "interval"."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        controls = getattr(window, "NoyvjTime", None)
    except ImportError:
        controls = None
    if controls is not None and getattr(controls, "start", None) is not None:
        controls.start("trade-empire", create_proxy(tick), TICK_INTERVAL_MS)
        return "shared"
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    return "interval"
