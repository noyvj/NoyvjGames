"""Continuum — a sustainable city across the ages.

Runs in-browser via Pyodide. This file is the browser layer only: it owns
the DOM, the event handlers, and the rendering. All of the actual thinking
lives in the engine modules that sit beside it —

    sim.py             city simulation core (population, resources, land)
    sustainability.py  the livability score (Milestone 2)
    research.py        the research tree engine (Milestone 3)
    save.py            the continuous-save / era-snapshot schema (Milestone 4)
    info_content.py    real-world info-panel content, keyed by era (Milestone 5)
    log.py             the ongoing log / diegetic feedback system (Milestone 6)
    visual.py          state -> visual data contract for the Three.js layer (Phase 5)

— which is the separation the design doc's tech notes ask for, so that six
more eras of content land in the engines rather than in one tangled file.
`info_page.py` (the render/toggle logic itself) is `shared/info_page.py`,
the same module the 8 climate-quartet games use — fetched into Pyodide's
virtual filesystem by index.html the same way canopy's boot script does.

Phase 1 complete: the Tribal-era season loop, the sustainability panel, the
research panel, the collapsed real-world info panel, and the shared save
widget's get_state()/load_state() contract. Phase 2's log and era-transition
systems land here too, since both are things the player reads.
"""

import importlib
import os
import sys
import types

# index.html writes the engine modules into Pyodide's virtual filesystem
# (the working directory) before running this file; make sure that
# directory is importable. Harmless under pytest, where conftest.py has
# already put the game directory on the path.
_HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import continuum_runstate as runstate  # noqa: E402 (needs the game folder on sys.path, set up just above)

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/continuum/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "continuum_runstate",
    "continuum_base",
    "continuum_founders",
    "continuum_achievements",
    "continuum_clock",
    "continuum_archive",
    "continuum_dynasty",
    "continuum_beyond",
    "continuum_techdebt",
    "continuum_heritage",
    "continuum_infopanels",
    "continuum_savestate",
    "continuum_timelapse",
    "continuum_citizens",
    "continuum_panels",
    "continuum_challenge",
    "continuum_geography",
    "continuum_progress",
    "continuum_extras",
    "continuum_peers",
    "continuum_views",
    "continuum_orders",
    "continuum_scenario",
    "continuum_hamlet",
    "continuum_advance",
    "continuum_advisors",
    "continuum_renderer",
    "continuum_setup",
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
    """game.state & co. live in continuum_runstate (they get replaced while playing), so reads go there; a write to
    any name copies to every module that holds the name, so monkeypatching a function or setting
    game._challenge_utc_today_override = "X" still changes what the code uses."""

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

