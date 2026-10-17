"""Le Champ de Mots — arcade minigame family (Milestones 27-30).

Four fast-paced, opt-in arcade modes, each themed to a natural grouping of
syllabus weeks and reusing the real catalog content and question-generation
machinery from `game.py` -- but with genuinely different, high-energy
interaction patterns than the core farm's calm SRS drilling: timers,
scoring, streaks, visual motion.

**Why this is a separate file, not a new mode inside game.py:** the core
farm's daily habit-forming loop is a *deliberate* zero-clock-pressure design
(CLAUDE.md §3/§8, Milestone 7) -- no `setInterval`/`setTimeout`/
`requestAnimationFrame`/`datetime`/`time.time` anywhere in `game.py`, and no
`@keyframes`/`animation:`/`transition:` anywhere in `style.css`, both
enforced by literal substring-scanning tests in `tests/test_polish.py`
(`test_the_farm_has_no_animation`, `test_nothing_in_the_game_runs_on_a_timer`).
That constraint protects the farm's own no-guilt, no-pressure habit loop; it
was never meant to ban a *separate, opt-in* arcade mode from having real
timers and motion -- an arcade minigame with a countdown and a moving racer
is a genuinely different thing, the same way "per-game / per-mode styling is
free once you're inside it" already works elsewhere in this hub. Rather than
loosen or reinterpret the two farm tests, this file (and `minigames.css`)
sits entirely outside what they scan, so the wellbeing guarantee for the
farm's own loop stays exactly as strict as it always was, unchanged, while
this file is free to use real timers and CSS motion. `game.py` imports this
module and re-exports only the handful of tick functions JS needs to reach
by name (see the bottom of `game.py`); every other piece of DOM wiring is
self-contained here via this module's own `setup()`.

**No circular import.** `game.py` imports this module, so this module never
imports `game.py` back -- the catalog-access/question-generation machinery
it reuses (`generate_question()`, `variants_for()`, the live `FarmState`)
is handed in once via `configure()`, called from `game.py`'s own `setup()`.
`document`/`create_proxy` are imported directly here, the same way `game.py`
imports them -- both are already faked by the test harness (or provided by
Pyodide) by the time this module loads.

**The "timer" is JS-driven, not a Python clock.** Every countdown in this
file is a plain integer/float counter that some explicit function
decrements -- `blitz_tick()`, `racer_tick()`, `boutique_tick()`, and
`cafe_tick()` are the JS-callable entry points, called from a `setInterval`
in `index.html`. Python only ever *owns the state*; JS owns real-world
timing, exactly the same split-of-responsibility the shared save widget and
the answer-report sender already established for this game.

**Row-unlock gating applies here too.** Every minigame only ever draws
content from `farm.is_row_unlocked(sequence)` rows, the same spoiler-
avoidance rule every other secondary mode (Review, Proficiency, Bonus,
Liaison, Cultural Notes) already follows. If a minigame's target sequence
range isn't fully unlocked yet, its toggle button is visible but disabled,
with the same "opens when row N has all sprouted" visual language locked
rows already use elsewhere in this game.
"""

import importlib
import sys
import types

# ---------------------------------------------------------------------------
# File map: this file is the entry point. Everything else lives in the modules named in _PART_NAMES, in dependency
# order (a module only imports from the ones before it). See "File map" in games/champ-de-mots/CLAUDE.md for what each
# one holds. The same list (as .py file names) is CHAMP_PY_MODULES in boot.js. game.py imports this module and
# calls configure(), configure_speech() and setup() on it, exactly as before the split.
# ---------------------------------------------------------------------------
_PART_NAMES = (
    "champ_minigames_rules",
    "champ_minigames_runstate",
    "champ_minigames_core",
    "champ_minigames_blitz",
    "champ_minigames_racer",
    "champ_minigames_boutique",
    "champ_minigames_cafe",
    "champ_minigames_sprint",
    "champ_minigames_arcade",
    "champ_minigames_games",
    "champ_minigames_amis",
    "champ_minigames_registry",
)
_PARTS = [importlib.import_module(_name) for _name in _PART_NAMES]
import champ_minigames_runstate as runstate
_LIVE = frozenset(runstate.LIVE_NAMES)

# Every name the old single-file minigames.py had is still reachable as minigames.<name> (game.py, tests and the page use them).
for _part in _PARTS:
    for _name, _value in vars(_part).items():
        if not _name.startswith("__") and _name not in _LIVE:
            globals()[_name] = _value
del _part, _name, _value


class _MinigamesModule(types.ModuleType):
    """minigames.blitz_active & co. live in champ_minigames_runstate (they get replaced while playing), so reads go
    there; a write to any name copies to every module that holds the name, so monkeypatching a function or setting
    minigames.on_amis_loaded = render still changes what the code uses."""

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
    sys.modules[__name__].__class__ = _MinigamesModule
except TypeError:  # a host without module subclassing: plain names still work, only the forwarding is lost
    pass
