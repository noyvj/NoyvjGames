"""SOL: Solar System Incremental Clicker (the entry point; see "File map" in CLAUDE.md).

Runs in the browser through Pyodide. This file imports the sol_*.py parts, forwards the live game variables and holds
the start-up wiring (setup, the tick loop).
"""

import importlib
import sys
import types

import json

from js import document, setInterval
from pyodide.ffi import create_proxy

import sol_runstate as runstate
from sol_capsules import _load_capsules
from sol_ghost import _ghost_reload_live, _load_pb_ghost, _refresh_ghost_strip
from sol_handlers import (
    on_asteroid_belt_buy_generator, on_asteroid_belt_buy_recycler, on_asteroid_belt_buy_trade_route,
    on_asteroid_belt_click, on_asteroid_belt_cycle_trade_destination, on_blueprint_ghost_click,
    on_blueprint_import, on_blueprint_make, on_budget_decrease, on_budget_increase, on_build_plan_add,
    on_build_plan_clear_done, on_build_plan_click, on_build_plan_copy, on_build_plan_suggest,
    on_capsules_click, on_charter_click, on_comet_click, on_compare_run, on_copy_share_card,
    on_dismiss_away_report, on_doctrine_click, on_earth_buy_generator, on_earth_buy_recycler,
    on_earth_buy_trade_route, on_earth_click, on_earth_cycle_trade_destination, on_export_stats,
    on_import_stats, on_jupiter_moons_buy_generator, on_jupiter_moons_buy_recycler,
    on_jupiter_moons_buy_sky_city, on_jupiter_moons_buy_trade_route, on_jupiter_moons_click,
    on_jupiter_moons_cycle_trade_destination, on_mars_buy_generator, on_mars_buy_recycler,
    on_mars_buy_trade_route, on_mars_click, on_mars_cycle_trade_destination, on_moon_buy_generator,
    on_moon_buy_recycler, on_moon_buy_trade_route, on_moon_click, on_moon_cycle_trade_destination,
    on_observatory_click, on_overview_click, on_pluto_buy_generator, on_pluto_buy_recycler,
    on_pluto_buy_trade_route, on_pluto_click, on_pluto_cycle_trade_destination, on_prestige,
    on_prestige_tree_click, on_priority_balance, on_priority_ecology, on_priority_growth,
    on_research_node_click, on_research_tree_click, on_reset_asteroid_belt, on_reset_earth,
    on_reset_jupiter_moons, on_reset_mars, on_reset_moon, on_reset_pluto, on_reset_saturn_moons,
    on_reset_venus, on_return_to_earth_from_asteroid_belt, on_return_to_earth_from_away_view,
    on_return_to_earth_from_jupiter_moons, on_return_to_earth_from_mars, on_return_to_earth_from_moon,
    on_return_to_earth_from_pluto, on_return_to_earth_from_saturn_moons, on_return_to_earth_from_venus,
    on_saturn_moons_buy_generator, on_saturn_moons_buy_recycler, on_saturn_moons_buy_sky_city,
    on_saturn_moons_buy_trade_route, on_saturn_moons_click, on_saturn_moons_cycle_trade_destination,
    on_scarcity_click, on_scarcity_leave, on_splits_click, on_toggle_achievements, on_toggle_build_plan,
    on_toggle_capsules, on_toggle_chains, on_toggle_changelog, on_toggle_charter, on_toggle_doctrine,
    on_toggle_epilogue, on_toggle_governor_report, on_toggle_observatory, on_toggle_overview,
    on_toggle_prestige_tree, on_toggle_sandbox, on_toggle_scarcity, on_toggle_splits, on_toggle_stats,
    on_travel_asteroid_belt, on_travel_jupiter_moons, on_travel_mars, on_travel_moon, on_travel_pluto,
    on_travel_saturn_moons, on_travel_venus, on_venus_buy_generator, on_venus_buy_recycler,
    on_venus_buy_trade_route, on_venus_click, on_venus_cycle_trade_destination,
)
from sol_rules import TICK_INTERVAL_MS
from sol_run import _full_render, tick
from sol_savestate import serialize_state

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/sol/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "sol_runstate",
    "sol_rules",
    "sol_util",
    "sol_story",
    "sol_runmods",
    "sol_scarcity",
    "sol_econ",
    "sol_rhythm",
    "sol_observatory",
    "sol_codex",
    "sol_charter",
    "sol_doctrines",
    "sol_sim",
    "sol_headless",
    "sol_achievements",
    "sol_panels",
    "sol_statsview",
    "sol_planner",
    "sol_overview",
    "sol_actions",
    "sol_capsules",
    "sol_savestate",
    "sol_scarcity_run",
    "sol_ghost",
    "sol_scarcity_panel",
    "sol_charter_panel",
    "sol_run",
    "sol_session",
    "sol_handlers",
)
_PARTS = [importlib.import_module(_name) for _name in _PART_NAMES]
_LIVE = frozenset(runstate.LIVE_NAMES)

# Every name the old single-file game.py had is still reachable as game.<name> (tests and the page use them).
for __part in _PARTS:
    for __name, __value in vars(__part).items():
        if not __name.startswith("__") and __name not in _LIVE:
            globals()[__name] = __value
del __part, __name, __value


class _GameModule(types.ModuleType):
    """game.state & co. live in sol_runstate (they get replaced while playing), so reads go there; a write to
    any name copies to every module that holds the name, so monkeypatching game._write_local_storage_item or
    setting game.state = fresh still changes what the code uses."""

    def __getattr__(self, name):
        if name in _LIVE:
            return getattr(runstate, name)
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name, value):
        if name in _LIVE:
            setattr(runstate, name, value)
            return
        for _part in _PARTS:
            if name in vars(_part):
                setattr(_part, name, value)
        super().__setattr__(name, value)

    def __dir__(self):
        return sorted(set(super().__dir__()) | _LIVE)


try:
    sys.modules[__name__].__class__ = _GameModule
except TypeError:  # a host without module subclassing: plain names still work, only the forwarding is lost
    pass


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
        controls.start("sol", create_proxy(tick), TICK_INTERVAL_MS)
        return "shared"
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    return "interval"


def setup():
    earth_click = document.getElementById("click-button")
    earth_click.innerText = "Mine Iron"
    earth_click.disabled = False
    earth_click.addEventListener("click", create_proxy(on_earth_click))

    earth_buy_generator = document.getElementById("buy-generator-button")
    earth_buy_generator.disabled = False
    earth_buy_generator.addEventListener("click", create_proxy(on_earth_buy_generator))

    earth_buy_recycler = document.getElementById("buy-recycler-button")
    earth_buy_recycler.disabled = False
    earth_buy_recycler.addEventListener("click", create_proxy(on_earth_buy_recycler))

    earth_buy_trade_route = document.getElementById("buy-trade-route-button")
    earth_buy_trade_route.disabled = False
    earth_buy_trade_route.addEventListener("click", create_proxy(on_earth_buy_trade_route))

    earth_cycle_trade_destination = document.getElementById("cycle-trade-destination-button")
    earth_cycle_trade_destination.innerText = "Change Destination"
    earth_cycle_trade_destination.disabled = False
    earth_cycle_trade_destination.addEventListener("click", create_proxy(on_earth_cycle_trade_destination))

    mars_click = document.getElementById("mars-click-button")
    mars_click.innerText = "Extract Ice"
    mars_click.disabled = False
    mars_click.addEventListener("click", create_proxy(on_mars_click))

    mars_buy_generator = document.getElementById("mars-buy-generator-button")
    mars_buy_generator.disabled = False
    mars_buy_generator.addEventListener("click", create_proxy(on_mars_buy_generator))

    mars_buy_recycler = document.getElementById("mars-buy-recycler-button")
    mars_buy_recycler.disabled = False
    mars_buy_recycler.addEventListener("click", create_proxy(on_mars_buy_recycler))

    mars_buy_trade_route = document.getElementById("mars-buy-trade-route-button")
    mars_buy_trade_route.disabled = False
    mars_buy_trade_route.addEventListener("click", create_proxy(on_mars_buy_trade_route))

    mars_cycle_trade_destination = document.getElementById("mars-cycle-trade-destination-button")
    mars_cycle_trade_destination.innerText = "Change Destination"
    mars_cycle_trade_destination.disabled = False
    mars_cycle_trade_destination.addEventListener("click", create_proxy(on_mars_cycle_trade_destination))

    document.getElementById("mars-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_mars)
    )

    moon_click = document.getElementById("moon-click-button")
    moon_click.innerText = "Mine Regolith"
    moon_click.disabled = False
    moon_click.addEventListener("click", create_proxy(on_moon_click))

    moon_buy_generator = document.getElementById("moon-buy-generator-button")
    moon_buy_generator.disabled = False
    moon_buy_generator.addEventListener("click", create_proxy(on_moon_buy_generator))

    moon_buy_recycler = document.getElementById("moon-buy-recycler-button")
    moon_buy_recycler.disabled = False
    moon_buy_recycler.addEventListener("click", create_proxy(on_moon_buy_recycler))

    moon_buy_trade_route = document.getElementById("moon-buy-trade-route-button")
    moon_buy_trade_route.disabled = False
    moon_buy_trade_route.addEventListener("click", create_proxy(on_moon_buy_trade_route))

    moon_cycle_trade_destination = document.getElementById("moon-cycle-trade-destination-button")
    moon_cycle_trade_destination.innerText = "Change Destination"
    moon_cycle_trade_destination.disabled = False
    moon_cycle_trade_destination.addEventListener("click", create_proxy(on_moon_cycle_trade_destination))

    document.getElementById("moon-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_moon)
    )

    venus_click = document.getElementById("venus-click-button")
    venus_click.innerText = "Collect Sulfur"
    venus_click.disabled = False
    venus_click.addEventListener("click", create_proxy(on_venus_click))

    venus_buy_generator = document.getElementById("venus-buy-generator-button")
    venus_buy_generator.disabled = False
    venus_buy_generator.addEventListener("click", create_proxy(on_venus_buy_generator))

    venus_buy_recycler = document.getElementById("venus-buy-recycler-button")
    venus_buy_recycler.disabled = False
    venus_buy_recycler.addEventListener("click", create_proxy(on_venus_buy_recycler))

    venus_buy_trade_route = document.getElementById("venus-buy-trade-route-button")
    venus_buy_trade_route.disabled = False
    venus_buy_trade_route.addEventListener("click", create_proxy(on_venus_buy_trade_route))

    venus_cycle_trade_destination = document.getElementById("venus-cycle-trade-destination-button")
    venus_cycle_trade_destination.innerText = "Change Destination"
    venus_cycle_trade_destination.disabled = False
    venus_cycle_trade_destination.addEventListener("click", create_proxy(on_venus_cycle_trade_destination))

    document.getElementById("venus-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_venus)
    )

    asteroid_belt_click = document.getElementById("asteroidbelt-click-button")
    asteroid_belt_click.innerText = "Prospect Platinum"
    asteroid_belt_click.disabled = False
    asteroid_belt_click.addEventListener("click", create_proxy(on_asteroid_belt_click))

    asteroid_belt_buy_generator = document.getElementById("asteroidbelt-buy-generator-button")
    asteroid_belt_buy_generator.disabled = False
    asteroid_belt_buy_generator.addEventListener("click", create_proxy(on_asteroid_belt_buy_generator))

    asteroid_belt_buy_recycler = document.getElementById("asteroidbelt-buy-recycler-button")
    asteroid_belt_buy_recycler.disabled = False
    asteroid_belt_buy_recycler.addEventListener("click", create_proxy(on_asteroid_belt_buy_recycler))

    asteroid_belt_buy_trade_route = document.getElementById("asteroidbelt-buy-trade-route-button")
    asteroid_belt_buy_trade_route.disabled = False
    asteroid_belt_buy_trade_route.addEventListener("click", create_proxy(on_asteroid_belt_buy_trade_route))

    asteroid_belt_cycle_trade_destination = document.getElementById("asteroidbelt-cycle-trade-destination-button")
    asteroid_belt_cycle_trade_destination.innerText = "Change Destination"
    asteroid_belt_cycle_trade_destination.disabled = False
    asteroid_belt_cycle_trade_destination.addEventListener(
        "click", create_proxy(on_asteroid_belt_cycle_trade_destination)
    )

    document.getElementById("asteroidbelt-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_asteroid_belt)
    )

    pluto_click = document.getElementById("pluto-click-button")
    pluto_click.innerText = "Collect Tholins"
    pluto_click.disabled = False
    pluto_click.addEventListener("click", create_proxy(on_pluto_click))

    pluto_buy_generator = document.getElementById("pluto-buy-generator-button")
    pluto_buy_generator.disabled = False
    pluto_buy_generator.addEventListener("click", create_proxy(on_pluto_buy_generator))

    pluto_buy_recycler = document.getElementById("pluto-buy-recycler-button")
    pluto_buy_recycler.disabled = False
    pluto_buy_recycler.addEventListener("click", create_proxy(on_pluto_buy_recycler))

    pluto_buy_trade_route = document.getElementById("pluto-buy-trade-route-button")
    pluto_buy_trade_route.disabled = False
    pluto_buy_trade_route.addEventListener("click", create_proxy(on_pluto_buy_trade_route))

    pluto_cycle_trade_destination = document.getElementById("pluto-cycle-trade-destination-button")
    pluto_cycle_trade_destination.innerText = "Change Destination"
    pluto_cycle_trade_destination.disabled = False
    pluto_cycle_trade_destination.addEventListener("click", create_proxy(on_pluto_cycle_trade_destination))

    document.getElementById("pluto-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_pluto)
    )

    jupiter_moons_click = document.getElementById("jupitermoons-click-button")
    jupiter_moons_click.innerText = "Skim Helium-3"
    jupiter_moons_click.disabled = False
    jupiter_moons_click.addEventListener("click", create_proxy(on_jupiter_moons_click))

    jupiter_moons_buy_generator = document.getElementById("jupitermoons-buy-generator-button")
    jupiter_moons_buy_generator.disabled = False
    jupiter_moons_buy_generator.addEventListener("click", create_proxy(on_jupiter_moons_buy_generator))

    jupiter_moons_buy_recycler = document.getElementById("jupitermoons-buy-recycler-button")
    jupiter_moons_buy_recycler.disabled = False
    jupiter_moons_buy_recycler.addEventListener("click", create_proxy(on_jupiter_moons_buy_recycler))

    jupiter_moons_buy_trade_route = document.getElementById("jupitermoons-buy-trade-route-button")
    jupiter_moons_buy_trade_route.disabled = False
    jupiter_moons_buy_trade_route.addEventListener("click", create_proxy(on_jupiter_moons_buy_trade_route))

    jupiter_moons_cycle_trade_destination = document.getElementById("jupitermoons-cycle-trade-destination-button")
    jupiter_moons_cycle_trade_destination.innerText = "Change Destination"
    jupiter_moons_cycle_trade_destination.disabled = False
    jupiter_moons_cycle_trade_destination.addEventListener(
        "click", create_proxy(on_jupiter_moons_cycle_trade_destination)
    )

    jupiter_moons_buy_sky_city = document.getElementById("jupitermoons-buy-sky-city-button")
    jupiter_moons_buy_sky_city.disabled = False
    jupiter_moons_buy_sky_city.addEventListener("click", create_proxy(on_jupiter_moons_buy_sky_city))

    document.getElementById("jupitermoons-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_jupiter_moons)
    )

    saturn_moons_click = document.getElementById("saturnmoons-click-button")
    saturn_moons_click.innerText = "Condense Methane"
    saturn_moons_click.disabled = False
    saturn_moons_click.addEventListener("click", create_proxy(on_saturn_moons_click))

    saturn_moons_buy_generator = document.getElementById("saturnmoons-buy-generator-button")
    saturn_moons_buy_generator.disabled = False
    saturn_moons_buy_generator.addEventListener("click", create_proxy(on_saturn_moons_buy_generator))

    saturn_moons_buy_recycler = document.getElementById("saturnmoons-buy-recycler-button")
    saturn_moons_buy_recycler.disabled = False
    saturn_moons_buy_recycler.addEventListener("click", create_proxy(on_saturn_moons_buy_recycler))

    saturn_moons_buy_trade_route = document.getElementById("saturnmoons-buy-trade-route-button")
    saturn_moons_buy_trade_route.disabled = False
    saturn_moons_buy_trade_route.addEventListener("click", create_proxy(on_saturn_moons_buy_trade_route))

    saturn_moons_cycle_trade_destination = document.getElementById("saturnmoons-cycle-trade-destination-button")
    saturn_moons_cycle_trade_destination.innerText = "Change Destination"
    saturn_moons_cycle_trade_destination.disabled = False
    saturn_moons_cycle_trade_destination.addEventListener(
        "click", create_proxy(on_saturn_moons_cycle_trade_destination)
    )

    saturn_moons_buy_sky_city = document.getElementById("saturnmoons-buy-sky-city-button")
    saturn_moons_buy_sky_city.disabled = False
    saturn_moons_buy_sky_city.addEventListener("click", create_proxy(on_saturn_moons_buy_sky_city))

    document.getElementById("saturnmoons-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_saturn_moons)
    )

    document.getElementById("research-node-list").addEventListener("click", create_proxy(on_research_node_click))

    document.getElementById("priority-growth-button").addEventListener(
        "click", create_proxy(on_priority_growth)
    )
    document.getElementById("priority-balance-button").addEventListener(
        "click", create_proxy(on_priority_balance)
    )
    document.getElementById("priority-ecology-button").addEventListener(
        "click", create_proxy(on_priority_ecology)
    )
    document.getElementById("budget-increase-button").addEventListener(
        "click", create_proxy(on_budget_increase)
    )
    document.getElementById("budget-decrease-button").addEventListener(
        "click", create_proxy(on_budget_decrease)
    )

    document.getElementById("travel-moon-button").addEventListener("click", create_proxy(on_travel_moon))
    document.getElementById("travel-mars-button").addEventListener("click", create_proxy(on_travel_mars))
    document.getElementById("travel-venus-button").addEventListener("click", create_proxy(on_travel_venus))
    document.getElementById("travel-asteroid-belt-button").addEventListener(
        "click", create_proxy(on_travel_asteroid_belt)
    )
    document.getElementById("travel-pluto-button").addEventListener("click", create_proxy(on_travel_pluto))
    document.getElementById("travel-jupiter-moons-button").addEventListener(
        "click", create_proxy(on_travel_jupiter_moons)
    )
    document.getElementById("travel-saturn-moons-button").addEventListener(
        "click", create_proxy(on_travel_saturn_moons)
    )
    document.getElementById("return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_away_view)
    )

    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("stats-toggle-button").addEventListener("click", create_proxy(on_toggle_stats))
    document.getElementById("copy-share-card-button").addEventListener(
        "click", create_proxy(on_copy_share_card)
    )
    document.getElementById("governor-report-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_governor_report)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("prestige-button").addEventListener("click", create_proxy(on_prestige))
    document.getElementById("sandbox-toggle-button").addEventListener("click", create_proxy(on_toggle_sandbox))
    document.getElementById("epilogue-button").addEventListener("click", create_proxy(on_toggle_epilogue))
    document.getElementById("epilogue-close-button").addEventListener("click", create_proxy(on_toggle_epilogue))
    document.getElementById("overview-toggle-button").addEventListener("click", create_proxy(on_toggle_overview))
    document.getElementById("overview-panel").addEventListener("click", create_proxy(on_overview_click))
    document.getElementById("build-plan-toggle-button").addEventListener("click", create_proxy(on_toggle_build_plan))
    document.getElementById("build-plan-add-button").addEventListener("click", create_proxy(on_build_plan_add))
    document.getElementById("build-plan-suggest-button").addEventListener(
        "click", create_proxy(on_build_plan_suggest)
    )
    document.getElementById("build-plan-clear-done-button").addEventListener(
        "click", create_proxy(on_build_plan_clear_done)
    )
    document.getElementById("build-plan-list").addEventListener("click", create_proxy(on_build_plan_click))
    document.getElementById("build-plan-copy-button").addEventListener("click", create_proxy(on_build_plan_copy))
    document.getElementById("splits-toggle-button").addEventListener("click", create_proxy(on_toggle_splits))
    document.getElementById("splits-panel").addEventListener("click", create_proxy(on_splits_click))
    document.getElementById("scarcity-toggle-button").addEventListener("click", create_proxy(on_toggle_scarcity))
    document.getElementById("scarcity-panel").addEventListener("click", create_proxy(on_scarcity_click))
    document.getElementById("scarcity-leave-button").addEventListener("click", create_proxy(on_scarcity_leave))
    document.getElementById("chains-toggle-button").addEventListener("click", create_proxy(on_toggle_chains))
    document.getElementById("blueprint-make-button").addEventListener("click", create_proxy(on_blueprint_make))
    document.getElementById("blueprint-import-button").addEventListener("click", create_proxy(on_blueprint_import))
    document.getElementById("blueprint-ghost").addEventListener("click", create_proxy(on_blueprint_ghost_click))
    document.getElementById("doctrine-toggle-button").addEventListener("click", create_proxy(on_toggle_doctrine))
    document.getElementById("doctrine-panel").addEventListener("click", create_proxy(on_doctrine_click))
    document.getElementById("charter-toggle-button").addEventListener("click", create_proxy(on_toggle_charter))
    document.getElementById("charter-panel").addEventListener("click", create_proxy(on_charter_click))
    document.getElementById("observatory-toggle-button").addEventListener("click", create_proxy(on_toggle_observatory))
    document.getElementById("observatory-panel").addEventListener("click", create_proxy(on_observatory_click))
    document.getElementById("comet-strip").addEventListener("click", create_proxy(on_comet_click))
    document.getElementById("capsules-toggle-button").addEventListener("click", create_proxy(on_toggle_capsules))
    document.getElementById("capsules-panel").addEventListener("click", create_proxy(on_capsules_click))
    document.getElementById("prestige-tree-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_prestige_tree)
    )
    document.getElementById("prestige-tree-panel").addEventListener("click", create_proxy(on_prestige_tree_click))
    document.getElementById("away-report-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_away_report)
    )
    document.getElementById("compare-run-button").addEventListener("click", create_proxy(on_compare_run))
    document.getElementById("stats-export-button").addEventListener("click", create_proxy(on_export_stats))
    document.getElementById("stats-import-button").addEventListener("click", create_proxy(on_import_stats))
    document.getElementById("research-tree").addEventListener("click", create_proxy(on_research_tree_click))

    document.getElementById("reset-world-button").addEventListener("click", create_proxy(on_reset_earth))
    document.getElementById("mars-reset-world-button").addEventListener("click", create_proxy(on_reset_mars))
    document.getElementById("moon-reset-world-button").addEventListener("click", create_proxy(on_reset_moon))
    document.getElementById("venus-reset-world-button").addEventListener("click", create_proxy(on_reset_venus))
    document.getElementById("asteroidbelt-reset-world-button").addEventListener(
        "click", create_proxy(on_reset_asteroid_belt)
    )
    document.getElementById("pluto-reset-world-button").addEventListener("click", create_proxy(on_reset_pluto))
    document.getElementById("jupitermoons-reset-world-button").addEventListener(
        "click", create_proxy(on_reset_jupiter_moons)
    )
    document.getElementById("saturnmoons-reset-world-button").addEventListener(
        "click", create_proxy(on_reset_saturn_moons)
    )

    _load_capsules()  # A-17: the capsules this browser kept (never part of a save)
    _load_pb_ghost()  # A-29: the personal-best recording this browser kept (never part of a save)
    _ghost_reload_live()
    _full_render()
    _refresh_ghost_strip()

    _start_tick_loop()


runstate._PRISTINE_JSON = json.dumps(serialize_state())  # A-11: the fresh-game state every Scarcity Run starts from
setup()
