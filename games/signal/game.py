"""Signal -- a daily deduction puzzle with a retro radio-room feel.

Hidden transmitters broadcast on a small grid. A "ping" on a tile returns ONE
number: the sum of every transmitter's signal at that tile, where a single
transmitter's signal is max(0, radius - manhattan_distance). You have a small
ping budget, then you must mark the exact tiles of every transmitter and
commit.

This file is the ENGINE's entry point. The rules live in the signal_*.py modules it
imports (see "File map" in CLAUDE.md): the seeded generator, the constraint solver
that proves each puzzle is solvable, scoring, streaks, achievements, the share
text, and the save/load contract. The engine never touches the DOM.
index.html's small glue script (app.js) draws whatever the engine
returns and forwards taps to it, so the engine runs the same under plain
CPython/pytest (the tests) and under Pyodide (the browser).

Public surface (what app.js and the shared save widget call):
    handle(request)  -- one JSON request in, one JSON response out
    get_state()      -- plain JSON-safe dict (shared/save-widget.js contract)
    load_state(data) -- merges a saved dict in (the inverse of get_state)

The rest of this docstring is the data model, because the save format is the
part that must never drift:

    {
      "schema": 1,
      "days":  {"YYYY-MM-DD:mode": {"mode", "kind": "daily"|"archive",
                                     "pings": [[r, c, reading], ...],
                                     "marks": [[r, c], ...], "guess": [[r, c], ...],
                                     "result": "inprogress"|"won"|"lost",
                                     "pings_used": n, "par": n|null}},
      "practice": null | {"code", "mode", "kind": "practice", ...same fields...},
      "practice_stats": {"easy": {"played", "won", "pings_hist"}, ...},
      "settings": {"mode", "assist_shading", "ascii_share", "show_streaks", "last_preset"},
      "earned": {"achievement_id": "YYYY-MM-DD"},
      "flags": {"shared": bool},
      "onboarding_seen": bool,
      "session": {"type", "date", "mode", "marks"},
      "achievements_earned": [ids]   # derived projection, never read back
      "stats": {...}                 # derived projection, never read back
    }
"""

import importlib
import sys
import types

import signal_runstate as runstate

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/signal/CLAUDE.md for what each one holds.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "signal_runstate",
    "signal_rules",
    "signal_puzzle",
    "signal_share",
    "signal_records",
    "signal_session",
    "signal_actions",
    "signal_savestate",
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
    """game.S & co. live in signal_runstate (they get replaced while playing), so reads go there; a write to
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



