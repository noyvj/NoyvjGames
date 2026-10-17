"""Canopy — Deforestation & Carbon Sinks Game.

Runs in-browser via Pyodide. Milestone 1: grid of forest plots with a
state machine (PRESERVED/BARE/REPLANTING/RECOVERED) and click-driven
Clear/Replant actions. Milestone 2: passive standing value that compounds
the longer a plot stays PRESERVED/RECOVERED. Payout economics and soil
degradation land in later milestones.
"""

import importlib
import sys
import types

import canopy_runstate as runstate

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/canopy/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "canopy_runstate",
    "canopy_rules",
    "canopy_worldvars",
    "canopy_helpers",
    "canopy_valuation",
    "canopy_records",
    "canopy_weather",
    "canopy_effects",
    "canopy_clearcut",
    "canopy_plot",
    "canopy_forestlog",
    "canopy_gridview",
    "canopy_carbon",
    "canopy_lifetime",
    "canopy_community",
    "canopy_layout",
    "canopy_stakeholders",
    "canopy_plotsheet",
    "canopy_regions",
    "canopy_summary",
    "canopy_labui",
    "canopy_achievements",
    "canopy_infopanels",
    "canopy_ghost",
    "canopy_charts",
    "canopy_realworld",
    "canopy_forecast",
    "canopy_tend",
    "canopy_challenge",
    "canopy_almanac",
    "canopy_contracts",
    "canopy_levels",
    "canopy_vault",
    "canopy_expedition",
    "canopy_gbstate",
    "canopy_survey",
    "canopy_hazards",
    "canopy_session",
    "canopy_comfort",
    "canopy_sessionview",
    "canopy_savestate",
    "canopy_renderer",
    "canopy_handlers_core",
    "canopy_handlers_panels",
    "canopy_handlers_modes",
    "canopy_loading",
    "canopy_tick",
    "canopy_setup",
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
    """game.total_income & co. live in canopy_runstate (they get replaced while playing), so reads go there; a write to
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
