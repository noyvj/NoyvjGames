"""render(): redraws the whole page from the live game, calling every panel's own render function."""

from js import document

import trade_runstate as runstate
from trade_achievements import _sync_earned_and_toast, update_achievements_display
from trade_blackout import render_blackout
from trade_blueprints import render_blueprint_options
from trade_cartel import render_desk
from trade_chain_ui import render_chain
from trade_charter_ui import render_captains, render_crest, render_ribbon, update_charter_display
from trade_colony import (
    colony_states, galaxy_expansion_unlocked, outer_reaches_unlocked, umbral_reach_unlocked,
)
from trade_expedition import render_lab
from trade_ghost import render_ghost
from trade_guild import render_guild
from trade_mapview import render_map
from trade_modes import render_modes
from trade_panels_fleet import render_colony, render_needs_strip, render_ship
from trade_panels_systems import render_endgame, render_fleet_priority, render_market, render_research
from trade_research import max_automated_ships
from trade_sandbox import _sandbox_top_up
from trade_ships import automated_ship_count, ships
from trade_summary import throughput_text, update_summary_display
from trade_weather import render_weather


def render():
    # J22 -- targets the inner #profit-display-text span, not #profit-display
    # itself: the sale-spark burst appends transient children to the sibling
    # #sale-spark-container inside #profit-display, and overwriting
    # #profit-display's own innerText every render would wipe those children
    # out before their one-shot animation ever gets a frame to paint.
    _sandbox_top_up()
    document.getElementById("profit-display-text").innerText = (
        "Chain Builder: your corporation is set aside" if runstate.chain_active is not None
        else "Credits: unlimited (sandbox)" if runstate.sandbox_active and runstate.crisis_active is None else f"Total profit: {runstate.total_profit} credits"
    )
    document.getElementById("sale-log").innerText = runstate.sale_log[-1] if runstate.sale_log else "No sales yet."
    document.getElementById("automation-slots-display").innerText = (
        f"Automation slots: {automated_ship_count()}/{max_automated_ships()} used"
    )
    render_fleet_priority()
    render_endgame()
    render_ghost()  # Z-3e5
    render_guild()
    render_research()
    render_map()
    for ship in ships.values():
        render_ship(ship)
    for colony_id in colony_states:
        render_colony(colony_id)
    render_market()
    render_needs_strip()

    # Milestone 13: the Kepler Cluster's colony rows and its goods'
    # market rows stay hidden entirely until the expansion is unlocked
    # -- colony_states not having an entry for them yet is what keeps
    # render_colony() from ever being asked to render one prematurely.
    expansion_unlocked = galaxy_expansion_unlocked()
    document.getElementById("expansion-colonies-panel").hidden = not expansion_unlocked
    document.getElementById("expansion-market-panel").hidden = not expansion_unlocked

    # J13 — same hidden-until-relevant idiom, one tier further out.
    expansion2_unlocked = outer_reaches_unlocked()
    document.getElementById("expansion2-colonies-panel").hidden = not expansion2_unlocked
    document.getElementById("expansion2-market-panel").hidden = not expansion2_unlocked

    # J1 — and once more for the Umbral Deep.
    expansion3_unlocked = umbral_reach_unlocked()
    document.getElementById("expansion3-colonies-panel").hidden = not expansion3_unlocked
    document.getElementById("expansion3-market-panel").hidden = not expansion3_unlocked

    update_achievements_display()
    _sync_earned_and_toast()
    update_summary_display()
    update_charter_display()
    render_crest()
    render_ribbon()
    render_captains()
    render_blackout()
    render_weather()
    render_lab()
    render_blueprint_options()
    render_desk()
    render_chain()  # J-5
    render_modes()  # GN-17
    throughput_el = document.getElementById("throughput-display")
    if throughput_el is not None:
        throughput_el.innerText = throughput_text()
