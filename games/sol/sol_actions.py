"""Player actions behind the click handlers: mining, buying, research, trade destination, travel, away reports and per-world resets."""

import math

from js import document
from pyodide.ffi import create_proxy

import sol_runstate as runstate
from sol_charter import stamp_bonus
from sol_econ import (
    _forget_close_call_history, _recompute_research, _update_travel_progress, _yield_multiplier,
    current_trade_destination, generator_cost, other_real_planets, recycler_cost, research_node_cost,
    research_node_status, sky_city_local_cost, sky_city_mars_cost, trade_route_cost, update_ecology_display,
    update_generator_display, update_resource_display, update_sky_city_display, update_terraform_display,
    update_trade_display, update_travel_display,
)
from sol_planner import update_win_display
from sol_rhythm import _note_split, _player_action, _streak_click
from sol_rules import (
    GAS_GIANT_BODIES, MANUAL_LABOR_THRESHOLD, PLANETS, PLANET_DISPLAY_NAMES, QUICK_START_TICKS,
    RESEARCH_NODE_BY_ID, RESEARCH_TIERS, SWIFT_EXPANSION_TICKS, TICK_INTERVAL_MS, planet_state,
    researched_nodes,
)
from sol_runmods import anomaly_factor
from sol_scarcity import scarcity_yield
from sol_statsview import update_all_cross_summaries
from sol_story import _mark_visited
from sol_util import (
    _dom_id, _format_duration, _fresh_planet_state, _hide_all_views, _spawn_floater, press_feedback,
)


def research_node_action(node_id):
    """Buys one node. Returns True if it was bought."""
    node = RESEARCH_NODE_BY_ID.get(node_id)
    if node is None or research_node_status(node) != "available":
        return False
    earth = planet_state["Earth"]
    cost = research_node_cost(node)
    if earth["resource_count"] < cost:
        return False
    earth["resource_count"] -= cost
    before = runstate.completed_tiers
    researched_nodes.add(node_id)
    _recompute_research()
    if runstate.completed_tiers > before:
        tier = RESEARCH_TIERS[before]
        runstate.unlocked_bodies.update(tier["unlocks"])
        for body in tier["unlocks"]:
            _note_split(body)
        update_travel_display()
        update_all_cross_summaries()
        # Second achievement wave (A2/A13) -- checked at the exact moment
        # each level completes, since that's the one instant both "how many
        # ticks has this playthrough taken" and "has a generator ever
        # existed anywhere" are meaningful to compare against a fixed line.
        if runstate.completed_tiers == 1:
            if runstate.total_ticks <= QUICK_START_TICKS:
                runstate.quick_start_hit = True
            if not runstate.any_generator_ever_built:
                runstate.off_the_grid_hit = True
        if runstate.completed_tiers == len(RESEARCH_TIERS) and runstate.total_ticks <= SWIFT_EXPANSION_TICKS:
            runstate.swift_expansion_hit = True
    _player_action("research", "Earth")
    return True


def _cycle_trade_destination(planet):
    others = other_real_planets(planet)
    if others:
        current = current_trade_destination(planet)
        next_index = (others.index(current) + 1) % len(others) if current in others else 0
        planet_state[planet]["trade_destination"] = others[next_index]
        update_trade_display(planet)
    press_feedback(document.getElementById(_dom_id(planet, "cycle-trade-destination-button")))


def _mine(planet, event=None):
    # Manual mining always works, even during an ecological collapse that
    # halts automated production on that planet — otherwise a player who
    # lets health hit 0% with no resources banked could get permanently
    # stuck with no way to earn the resources needed to build a recovery
    # Recycler. Per the project's "no dead-end/unwinnable states" balance
    # rule, there must always be a lever.
    state = planet_state[planet]
    gained = (1 * _yield_multiplier() * _streak_click() * anomaly_factor("click") * (1 + stamp_bonus(planet))
              * scarcity_yield(planet))
    state["resource_count"] += gained
    runstate.total_manual_clicks += 1
    runstate.lifetime_resources_mined_by_click += gained
    if (
        planet == "Earth"
        and not runstate.manual_labor_hit
        and not runstate.any_generator_ever_built
        and state["resource_count"] >= MANUAL_LABOR_THRESHOLD
    ):
        runstate.manual_labor_hit = True
    update_resource_display(planet)
    button = document.getElementById(_dom_id(planet, "click-button"))
    _spawn_floater(button, "✦", "floater--spark", event)
    press_feedback(button)
    _player_action("mine", planet)


def _buy_generator(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-generator-button"))
    cost = generator_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["generator_count"] += 1
        runstate.lifetime_generators_built += 1
        runstate.any_generator_ever_built = True
        update_resource_display(planet)
        update_generator_display(planet)
        update_terraform_display(planet)
        _spawn_floater(button, "⚙️", "floater--build")
        _player_action("gen", planet)
    press_feedback(button)


def _buy_recycler(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-recycler-button"))
    cost = recycler_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["recycler_count"] += 1
        runstate.lifetime_recyclers_built += 1
        update_resource_display(planet)
        update_ecology_display(planet)
        update_terraform_display(planet)
        _spawn_floater(button, "♻️", "floater--build")
        _player_action("rec", planet)
    press_feedback(button)


def _buy_trade_route(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-trade-route-button"))
    destination = current_trade_destination(planet)
    if destination is not None:
        cost = trade_route_cost(planet, destination)
        if state["resource_count"] >= cost:
            state["resource_count"] -= cost
            state["trade_routes"][destination] = state["trade_routes"].get(destination, 0) + 1
            runstate.lifetime_trade_routes_built += 1
            update_resource_display(planet)
            update_trade_display(planet)
            update_terraform_display(planet)
            _spawn_floater(button, "🚀", "floater--build")
            _player_action("route", planet)
    press_feedback(button)


def _buy_sky_city(planet):
    # Milestone 10: only ever called for JupiterMoons/SaturnMoons. Requires
    # BOTH the local resource AND Mars's Water Ice — the trade system's
    # payoff. Press feedback always fires; state only changes if both costs
    # are affordable.
    state = planet_state[planet]
    mars_state = planet_state["Mars"]
    button = document.getElementById(_dom_id(planet, "buy-sky-city-button"))
    local_cost = sky_city_local_cost(planet)
    mars_cost = sky_city_mars_cost(planet)
    if state["resource_count"] >= local_cost and mars_state["resource_count"] >= mars_cost:
        state["resource_count"] -= local_cost
        mars_state["resource_count"] -= mars_cost
        state["sky_city_count"] += 1
        runstate.lifetime_sky_cities_built += 1
        update_resource_display(planet)
        update_resource_display("Mars")
        update_sky_city_display(planet)
        update_terraform_display(planet)
        _spawn_floater(button, "🏙️", "floater--build")
        _player_action("sky", planet)
    press_feedback(button)


# --- Travel (shared by the Travel buttons, Return-to-Earth, and the A9
# overview dashboard) plus A5's "while you were away" report ---
AWAY_REPORT_MIN_TICKS = 100  # 10 seconds of simulated play; shorter hops aren't worth a report


def _show_planet_view(planet):
    _hide_all_views()
    document.getElementById(f"{planet.lower()}-view").hidden = False
    update_resource_display(planet)
    update_generator_display(planet)
    update_ecology_display(planet)
    update_trade_display(planet)
    if planet in GAS_GIANT_BODIES:
        update_sky_city_display(planet)
    update_terraform_display(planet)
    update_all_cross_summaries()


def _snapshot_departure(planet):
    state = planet_state[planet]
    runstate._departure_snapshots[planet] = {
        "tick": runstate.total_ticks,
        "generated": state["governed_resource_generated"],
        "generators": state["generator_count"],
        "recyclers": state["recycler_count"],
        "ecology": state["ecology_health"],
    }


def _report_arrival(planet):
    """A5: on returning to a world, report what happened there while the
    player was elsewhere: resources its automation generated (real, already
    tracked as governed_resource_generated), what the Governor built, and
    how its ecology moved. Reports elapsed simulated play-time and never
    gates or advances anything, so it doesn't touch the no-idle-timer rule."""
    snap = runstate._departure_snapshots.pop(planet, None)
    if snap is None:
        return
    elapsed = runstate.total_ticks - snap["tick"]
    if elapsed < AWAY_REPORT_MIN_TICKS:
        return
    state = planet_state[planet]
    gained = math.floor(state["governed_resource_generated"] - snap["generated"] + 1e-9)
    generators = state["generator_count"] - snap["generators"]
    recyclers = state["recycler_count"] - snap["recyclers"]
    name = PLANET_DISPLAY_NAMES.get(planet, planet)
    parts = [f"+{max(gained, 0)} {PLANETS[planet]['resource_name']}"]
    if generators > 0 or recyclers > 0:
        parts.append(f"the Governor built {max(generators, 0)} generator(s) and {max(recyclers, 0)} Recycler(s)")
    else:
        parts.append("no Governor purchases")
    parts.append(f"ecology {round(snap['ecology'])}% to {round(state['ecology_health'])}%")
    document.getElementById("away-report-text").innerText = (
        f"While you were away from {name} ({_format_duration(elapsed * TICK_INTERVAL_MS / 1000)}): "
        + "; ".join(parts) + "."
    )
    document.getElementById("away-report").hidden = False


def _travel_to(planet):
    if planet != "Earth" and planet not in runstate.unlocked_bodies:
        return False
    if planet == runstate.current_planet:
        return True
    if runstate.current_planet in planet_state:
        _snapshot_departure(runstate.current_planet)
    runstate.current_planet = planet
    _mark_visited(planet)
    _update_travel_progress()
    _show_planet_view(planet)
    _report_arrival(planet)
    _player_action("travel", planet)
    return True


def _travel_from_button(planet, button_id):
    _travel_to(planet)
    press_feedback(document.getElementById(button_id))


def _return_to_earth():
    _travel_to("Earth")


# --- Reset this world only (A18) ---
# Distinct from a full save wipe (which the save-widget's own UI already
# offers): this only clears ONE planet's own economy -- resources,
# buildings, ecology, trade routes, terraforming -- back to its fresh-game
# defaults. Research/unlocked_bodies/visited_bodies/achievements/current_
# planet are all untouched, since re-locking a world you already unlocked
# via research (or "unvisiting" it) isn't what "reset this world" means.
#
# Z22 cross-game audit: this used to gate on a native browser confirm()
# dialog (`_confirm()`, a lazy `import js` per call). That predated
# shared/confirm-dialog.js entirely -- SOL is one of two games flagged as
# such (Aftermath's skill-tree reset is the other). Migrated to the shared
# ConfirmDialog for the same reasons every other game's reset/retire-style
# action already gets it: a native confirm() blocks Pyodide's whole event
# loop, can't offer "don't ask me again," and looks nothing like the rest
# of this site. Same `_confirm_dialog_ask()` helper shape as Grid's/Herd's/
# Loop's/Trade Empire's own copies (lazy `from js import window`, fall
# through to calling on_confirm() immediately when `window` or
# `window.ConfirmDialog` isn't available -- which is what the pytest
# fake-DOM harness's `js` module does by default, and what a page that
# somehow loaded without confirm-dialog.js would do too).
def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
    )


def _reset_world(planet):
    display_name = PLANET_DISPLAY_NAMES.get(planet, planet)

    def _do_reset():
        planet_state[planet] = _fresh_planet_state(planet)
        _forget_close_call_history(planet)
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
        update_terraform_display(planet)
        update_all_cross_summaries()
        update_win_display()
        press_feedback(document.getElementById(_dom_id(planet, "reset-world-button")))

    _confirm_dialog_ask(
        action_id=f"sol-reset-world-{planet}",
        message=(
            f"Reset {display_name}? This clears its resources, buildings, ecology, "
            "trade routes, and terraforming progress. Research, travel, and "
            "achievements are not affected. This cannot be undone."
        ),
        confirm_label=f"Reset {display_name}",
        on_confirm=_do_reset,
    )
