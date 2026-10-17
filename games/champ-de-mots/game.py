"""Le Champ de Mots — a French-syllabus farming game.

Runs in-browser via Pyodide, per the hub's default stack. Milestone 2: the
plant-state data model and the spaced-repetition scheduler underneath it
(design doc §6). Plots are built straight from the combined FREN151/FREN152
catalog and laid out as one continuous run of rows, sequence 1-23, with no
season break between the two courses.

Design doc §3's wellbeing constraint is enforced here rather than only in the
UI: a plot's visible growth stage only ever moves *up*. An incorrect recall
reschedules the plot sooner (it "needs water again") but never demotes the
plant, never removes it, and never produces a failure state.
"""

import importlib
import sys
import types

# Milestones 27-30: the arcade minigame family lives entirely in its own
# file (minigames.py) -- see that file's module docstring for the full
# wellbeing-constraint-exception rationale (the farm's own no-timer/
# no-animation tests scan only this file and style.css by name, so keeping
# every minigame's timer/animation code out of both files is what lets
# those tests keep passing completely unchanged). A plain `import minigames`
# is tried first -- in the browser, index.html writes minigames.py's source
# onto Pyodide's virtual filesystem before running this file, so the normal
# import machinery finds it on the default sys.path with no extra plumbing.
# The except branch is a pytest-harness fallback only: this file's own
# directory isn't necessarily on sys.path when game.py is loaded by
# importlib file-path (tests/conftest.py's approach), so that path is added
# and the import retried.
try:
    import minigames
except ImportError:  # pragma: no cover -- exercised by every test run
    import os as _os
    import sys as _sys

    _GAME_DIR = _os.path.dirname(_os.path.abspath(__file__))
    if _GAME_DIR not in _sys.path:
        _sys.path.insert(0, _GAME_DIR)
    import minigames

# JS calls a minigame's countdown tick by name via
# `pyodide.globals.get("...")` (the same lookup shared/save-widget.js uses
# for get_state()/load_state()) -- that only ever sees names bound in *this*
# module's namespace, not minigames.py's own, so each tick function needs a
# plain re-export here. This is a name binding, not a call to any of the
# banned timer APIs, so it doesn't trip test_nothing_in_the_game_runs_on_a_timer's
# substring scan over this file.
try:
    import formats  # FS-17 to FS-22: the exam practice formats (pure, DOM-free)
except ImportError:  # pragma: no cover -- pytest-harness fallback, same as minigames above
    import os as _os2
    import sys as _sys2

    _GAME_DIR2 = _os2.path.dirname(_os2.path.abspath(__file__))
    if _GAME_DIR2 not in _sys2.path:
        _sys2.path.insert(0, _GAME_DIR2)
    import formats
blitz_tick = minigames.blitz_tick
racer_tick = minigames.racer_tick
boutique_tick = minigames.boutique_tick
cafe_tick = minigames.cafe_tick
sprint_tick = minigames.sprint_tick
pairs_tick = minigames.pairs_tick
gaps_tick = minigames.gaps_tick
listenpick_tick = minigames.listenpick_tick
wordorder_tick = minigames.wordorder_tick
amis_tick = minigames.amis_tick
minigame_run_active = minigames.any_timed_run_active

# ---------------------------------------------------------------------------
# File map: this file is the entry point and the wiring. Everything else lives in the modules named in
# _PART_NAMES, in dependency order (a module only imports from the ones before it). See "File map" in
# games/champ-de-mots/CLAUDE.md for what each one holds. The same list (as .py file names) is CHAMP_PY_MODULES in boot.js.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "champ_rules",
    "champ_runstate",
    "champ_catalog",
    "champ_model",
    "champ_qbuild",
    "champ_questions",
    "champ_grading",
    "champ_labels",
    "champ_util",
    "champ_stats",
    "champ_calendar",
    "champ_points",
    "champ_reportlog",
    "champ_watering",
    "champ_growth",
    "champ_practice_base",
    "champ_reports",
    "champ_leech",
    "champ_semesters",
    "champ_arrange",
    "champ_legend",
    "champ_water_pool",
    "champ_review_base",
    "champ_review",
    "champ_proficiency",
    "champ_bonus",
    "champ_builder",
    "champ_listening",
    "champ_conversation",
    "champ_placement",
    "champ_examformats",
    "champ_phrasebook",
    "champ_dashboard",
    "champ_liaison",
    "champ_achievements",
    "champ_planner",
    "champ_accent",
    "champ_prefs",
    "champ_shop",
    "champ_practice",
    "champ_wateropts",
    "champ_farm",
    "champ_renderer",
    "champ_setup",
    "champ_savegame",
)
_PARTS = [importlib.import_module(_name) for _name in _PART_NAMES]
import champ_runstate as runstate
_LIVE = frozenset(runstate.LIVE_NAMES)

# Every name the old single-file game.py had is still reachable as game.<name> (tests and the page use them).
for _part in _PARTS:
    for _name, _value in vars(_part).items():
        if not _name.startswith("__") and _name not in _LIVE:
            globals()[_name] = _value
del _part, _name, _value


class _GameModule(types.ModuleType):
    """game.current_question & co. live in champ_runstate (they get replaced while playing), so reads go there; a
    write to any name copies to every module that holds the name, so monkeypatching a function or setting
    game.ACCENT_SENSITIVE = False still changes what the code uses."""

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

# The start-up call that ran at import time in the single-file game.py (setup() is defined in champ_setup).
from champ_setup import setup  # noqa: E402

setup()
