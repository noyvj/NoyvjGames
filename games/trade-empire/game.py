"""Trade Empire — Interstellar Trade Empire (working title).

Runs in-browser via Pyodide. Milestone 1: a founding-contract intro, one
ship, one manual route between two colonies. Milestone 2: a third colony
and a second ship — routes are no longer a fixed pair, each ship can be
manually sent to whichever colony the player chooses. Milestone 3: colony
need satisfaction scales output. Milestone 4: market prices fluctuate
with supply. Milestone 5: two more colonies and two more ships — no new
mechanic, just enough scale that manually running every ship/route by
hand gets genuinely busy, which is exactly the case Milestone 6's
automation exists to answer. Milestone 6: ships can be automated.
Milestone 7: a 2D map — colonies as nodes, routes as lines, drawn on a
canvas directly from Python via Pyodide's `js` module. Still no moving
ships on it (Milestone 11). Milestone 8: a small, flat research tree
(no prerequisites yet) spent from a separate, passively-accruing
research-points currency, gating an automation-slot expansion, a
fleet-wide speed boost, and a fleet-wide cargo boost. Milestone 9:
evolving needs v2 — sustained delivery develops a colony further, and
development expands what it needs (a second, cross-cycle need) rather
than ever "solving" it. Milestone 10: colony specialization — an
environmental, non-player-chosen strength/weakness pair per colony
(reflecting each one's flavor text) that activates automatically once
it develops. Milestone 11: ships render as moving dots on the map,
interpolated between origin and destination using each trip's own
fixed tick count so Fast Ships research can't retroactively distort a
ship already mid-flight. Milestone 12: fleet-level automation — with
every good needed by exactly one colony, a single automated ship's
route is already fixed, so "prioritization across routes" means
letting an idle automated ship abandon its home shuttle and reposition
empty to whichever producer feeds the fleet's most under-served
colony, when Fleet Priority mode is switched on. Milestone 13: galaxy
scaling — a research-gated second system, the Kepler Cluster, with its
own self-contained three-good need-triangle (so colony_needing() and
colony_producing() stay single-valued fleetwide) that links back to
the home system through each Kepler colony's secondary need, once
developed. Colony state for the cluster isn't created until the
research unlocks it, so it never contends with the home system's
colonies for Fleet Priority's attention beforehand. Milestone 14:
endgame — reaching a fully automated fleet, Fleet Priority, and the
Kepler Cluster all at once is treated as a soft win-state: the pattern
the player built is narrated as spreading to a growing, abstracted
background galaxy (hundreds of worlds by design, not hundreds of
individually simulated colonies -- a deliberate scope cut) that
trickles in passive revenue. The sandbox itself never ends or locks.
"""

import importlib
import sys
import types

import json

import trade_runstate as runstate
from trade_savestate import get_state
from trade_setup import setup

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/trade-empire/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "trade_runstate",
    "trade_rules",
    "trade_records",
    "trade_charter",
    "trade_uikit",
    "trade_colony",
    "trade_research",
    "trade_mapdraw",
    "trade_effects",
    "trade_market",
    "trade_hub",
    "trade_blueprints",
    "trade_captains",
    "trade_ships",
    "trade_crew",
    "trade_founding",
    "trade_guild",
    "trade_weather",
    "trade_blackout",
    "trade_crises",
    "trade_expedition",
    "trade_meridian",
    "trade_exchange",
    "trade_cartel",
    "trade_ghost",
    "trade_chain_rules",
    "trade_chain_logic",
    "trade_panels_fleet",
    "trade_panels_systems",
    "trade_mapview",
    "trade_achievements",
    "trade_summary",
    "trade_charter_ui",
    "trade_chain_ui",
    "trade_modes",
    "trade_savestate",
    "trade_loadparts",
    "trade_sandbox",
    "trade_renderer",
    "trade_loading",
    "trade_handlers_core",
    "trade_handlers_features",
    "trade_handlers_modes",
    "trade_tick",
    "trade_setup",
)
_PARTS = [importlib.import_module(_name) for _name in _PART_NAMES]
_LIVE = frozenset(runstate.LIVE_NAMES)

# Every name the old single-file game.py had is still reachable as game.<name> (tests and the page use them).
for _part in _PARTS:
    for _name, _value in vars(_part).items():
        if not _name.startswith("__") and _name not in _LIVE:
            globals()[_name] = _value
del _part, _name, _value


class _GameModule(types.ModuleType):
    """game.total_profit & co. live in trade_runstate (they get replaced while playing), so reads go there; a write to
    any name copies to every module that holds the name, so monkeypatching a function or setting
    game.run_seed = "X" still changes what the code uses."""

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


runstate._fresh_state = json.loads(json.dumps(get_state()))
setup()
