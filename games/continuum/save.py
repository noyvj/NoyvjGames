"""Continuum — save schema: one continuous save, with era revisits.

Milestone 4 of Phase 1. The design doc asks for "one continuous save
spanning the whole arc, with the ability to revisit/replay completed eras
without losing forward progress", planned early because retrofitting it
after several eras had been built linearly would be painful.

## How this reaches the backend

It doesn't — not directly. Per `planning/SAVE-BUTTON-INTEGRATION.md` the
hub now has one shared `shared/save-widget.js` that every game includes
unchanged, and the entire per-game contract is two functions:

    get_state()   -> one plain, JSON-safe dict
    load_state(d) -> restores it; the exact inverse

The widget POSTs that dict to the existing FastAPI/Neon save endpoints and
hands back a save code. It never looks *inside* the dict — so Continuum's
more involved needs are met simply by making that one dict structured:

    {
      "save_version": 1,
      "game": "continuum",
      "era_order":      [...],          # the arc this save was written against
      "current_era":    "tribal",       # what the player is playing right now
      "furthest_era":   "tribal",       # how far the campaign has actually got
      "revisiting":     null | era,     # set while replaying a completed era
      "current_state":  {"city": {...}, "research": [...]},
      "parked_state":   null | {...},   # forward progress, held during a revisit
      "era_snapshots":  {era: {...}},   # how each completed era ended
      "ui":             {...},          # view toggles worth preserving
      "log":            {...}           # the ongoing log (Milestone 6, see log.py)
    }

No bespoke save UI, no second bridge, no widget changes.

## How revisits work

`current_state` is always whatever is being played. When the player enters
a revisit, the live forward state is snapshotted into `parked_state` and
the requested era's snapshot is loaded into the live objects; leaving the
revisit puts the parked state back, untouched. `furthest_era` never moves
backwards, and a completed era's snapshot is never rewritten by a replay —
the record of how an era actually went the first time is the thing the
game's whole "what kind of city did you build" framing rests on.

Everything here mutates the `CityState` and `ResearchTree` objects it was
handed rather than replacing them, so references held elsewhere (game.py's
module-level `state` and `tree`) stay valid across a load.
"""

import copy
import math

import challenges
import log
import sim
import sustainability
import trajectory

SAVE_VERSION = 1
GAME_ID = "continuum"

# Every field of CityState that is genuinely state. Kept as an explicit
# list rather than a __dict__ sweep so that adding a field is a deliberate
# save-schema decision, and so a stray cached value can't leak into saves.
CITY_FIELDS = [
    "era",
    "season",
    "population",
    "growth_progress",
    "resources",
    "allocation",
    "buildings",
    "land_health",
    "pollution",
    "sprawl",
    "fed_fraction",
    "last_extraction",
    "last_sustainable_yield",
    "last_report",
    "score_history",
    # K12/K18 (planning/TODO.md) -- the starting scenario id and the
    # opt-in hard-mode flag. Both live on CityState (not Campaign) because
    # every sustainability.py component function already takes `state`,
    # not `campaign` -- see sustainability.py's own "K18" note for why
    # this is zero new plumbing rather than a signature change everywhere.
    "scenario",
    "hard_mode",
    # K11 / K19 / K25 / K10 -- validated field-by-field in restore_city().
    "challenge",
    "trajectory",
    "calm_streak",
]

# Fields that are dicts whose *key set* belongs to sim.py, not to the save:
# the resource list, the role list and the building list. A save carries
# their values only, so each is written key-by-key into the live dict and
# keys sim.py doesn't know about are dropped. Replacing them wholesale meant
# a save written before a later era added (say) a fifth role left the
# settlement with no entry for it, and the next season or render died on a
# KeyError — after the widget had already reported a successful load. It
# also keeps clamp_allocation()/role_diversity(), which both iterate
# sim.ROLES, safe against an allocation dict of some other shape.
CITY_KEYED_DICTS = ["resources", "allocation", "buildings"]

# Phase 4 audit: `resources`/`allocation`/`buildings` are counts/quantities
# that must never go negative, NaN or non-numeric — see the module-level
# audit note below for why. Buildings and allocation are always whole
# counts; resources are left as floats (surplus/food/etc. are fractional
# in normal play).
CITY_KEYED_DICTS_ARE_COUNTS = {"resources": False, "allocation": True, "buildings": True}

# A generous ceiling on `growth_progress`, purely defensive (Phase 4 audit).
# In legitimate play this value never strays far above 1.0 -- the season
# loop's own while-loop (see sim.CityState.advance_season()'s step 7)
# converts any excess into population the moment there's housing room, so
# it only ever sits above 1.0 at all while housing is fully capped, and
# even then accrues at most GROWTH_RATE (0.35) per season. A hand-edited
# save that sets this to something enormous would otherwise turn that same
# while-loop into an effectively unbounded iteration the instant the save
# loads and a season is advanced -- a real, reproducible page-freeze this
# audit pass found and is closing off here, not a hypothetical one.
GROWTH_PROGRESS_MAX = 10.0

# Every other CITY_FIELDS scalar that must be a real, finite number to mean
# anything at all: (low bound, high bound or None, cast-to-int). Discovered
# by this Phase 4 audit pass hand-loading adversarial saves -- see CLAUDE.md
# for the specific failure modes each one closes (a bad `era`/`population`/
# resource value used to load "successfully" and then crash, hang, or
# silently corrupt state on the very next season or render).
NUMERIC_FIELD_BOUNDS = {
    "population": (sim.MIN_POPULATION, None, True),
    "season": (1, None, True),
    "growth_progress": (0.0, GROWTH_PROGRESS_MAX, False),
    "land_health": (sim.MIN_LAND_HEALTH, 1.0, False),
    "pollution": (0.0, 1.0, False),
    "sprawl": (0.0, 1.0, False),
    "fed_fraction": (0.0, 1.0, False),
    "last_extraction": (0.0, None, False),
    "last_sustainable_yield": (0.0, None, False),
    "calm_streak": (0, 100000, True),
}


def _is_finite_number(value):
    """True for a real int/float — excludes bool, None, str, NaN, ±inf.

    A malicious or hand-edited save can put any JSON value in a numeric
    field's place; Python's own `json.loads` even accepts the non-standard
    `NaN`/`Infinity` tokens some other JSON implementations reject outright.
    Every numeric field this module restores is filtered through this
    before it's trusted.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _sanitize_numeric_field(value, bounds):
    """Clamps `value` into `bounds` (low, high, is_int); None if unusable."""
    if not _is_finite_number(value):
        return None
    low, high, is_int = bounds
    sanitized = float(value)
    if low is not None:
        sanitized = max(low, sanitized)
    if high is not None:
        sanitized = min(high, sanitized)
    return int(round(sanitized)) if is_int else sanitized


def city_snapshot(state):
    """A deep-copied, JSON-safe record of one CityState."""
    return {field: copy.deepcopy(getattr(state, field)) for field in CITY_FIELDS}


def restore_city(state, data):
    """Writes a city snapshot back into an existing CityState, in place.

    Missing fields keep their current value, so a save written before a
    field existed still loads — and, per CITY_KEYED_DICTS, that holds one
    level down as well.

    Phase 4 audit: every field that isn't a real, sane value for what it
    represents is now treated exactly like a *missing* field (kept at its
    current value) rather than trusted verbatim. Before this pass, a save
    with `population: "not-a-number"`, a resource/allocation/building value
    of `null`, a `land_health`/`pollution` outside its valid range, or an
    `era` string this build doesn't recognise all loaded "successfully" and
    then crashed or corrupted state on the very next season or render --
    the exact "widget already reported success" failure shape the
    Milestone 4 audit's own CITY_KEYED_DICTS fix was written to close for a
    different field. See CLAUDE.md's Phase 4 build notes for the specific
    cases this closes.
    """
    if not isinstance(data, dict):
        data = {}
    for field in CITY_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if field in CITY_KEYED_DICTS:
            if isinstance(value, dict):
                live = getattr(state, field)
                is_count = CITY_KEYED_DICTS_ARE_COUNTS[field]
                for key in live:
                    if key not in value:
                        continue
                    sanitized = _sanitize_numeric_field(value[key], (0.0, None, is_count))
                    if sanitized is not None:
                        live[key] = sanitized
        elif field == "era":
            # Validated against the schema's own source of truth rather than
            # trusted verbatim -- an unrecognised era string used to be
            # written straight into `state.era` (and, from there, into
            # `tree.current_era`), and the next call to `sim.era_index()`
            # anywhere -- the very next season, or a revisit's own
            # `_restore_snapshot()` -- raised ValueError. Reachable two ways:
            # a save's own `current_state.city.era`, and (since this same
            # function restores era snapshots too) a hand-edited
            # `era_snapshots` entry loaded back via a revisit.
            if value in sim.ERA_ORDER:
                state.era = value
        elif field == "scenario":
            # Same validate-against-the-schema's-own-source-of-truth
            # standard as `era` just above: an unrecognised scenario id
            # (a stale value from a future build, or a hand-edited save)
            # is treated as missing rather than trusted verbatim, so
            # `state.scenario` can never hold a value `sim.SCENARIOS`
            # doesn't know -- it stays whatever CityState.__init__() (or
            # a prior load) already set it to, which is always valid.
            if isinstance(value, str) and value in sim.SCENARIOS:
                state.scenario = value
        elif field == "hard_mode":
            if isinstance(value, bool):
                state.hard_mode = value
        elif field == "challenge":
            state.challenge = challenges.clean(value)
        elif field == "trajectory":
            state.trajectory = trajectory.clean_points(value)
        elif field == "score_history":
            if isinstance(value, list):
                cleaned = [float(v) for v in value if _is_finite_number(v)]
                setattr(state, field, cleaned)
        elif field in NUMERIC_FIELD_BOUNDS:
            sanitized = _sanitize_numeric_field(value, NUMERIC_FIELD_BOUNDS[field])
            if sanitized is not None:
                setattr(state, field, sanitized)
        else:
            setattr(state, field, copy.deepcopy(value))
    state.clamp_allocation()


def snapshot_of(state, tree, score=None):
    """A full record of a moment: the city, the tree, and the score."""
    if score is None:
        score = sustainability.score(state, tree.effects())
    return {
        "era": state.era,
        "season": state.season,
        "score": score,
        "city": city_snapshot(state),
        "research": tree.snapshot(),
    }


def _restore_snapshot(snapshot, state, tree):
    if not isinstance(snapshot, dict):
        snapshot = {}
    restore_city(state, snapshot.get("city"))
    tree.restore(snapshot.get("research"))
    tree.current_era = state.era


class Campaign:
    """One continuous playthrough: the live city, the tree, and the arc."""

    def __init__(self, state=None, tree=None):
        # Imported lazily-ish: research imports sim, and a default tree is
        # only needed when a caller doesn't supply one.
        if tree is None:
            import research

            tree = research.build_tree()
        self.state = state if state is not None else sim.CityState()
        self.tree = tree
        self.furthest_era = self.state.era
        self.revisiting = None
        self.parked_state = None
        self.era_snapshots = {}
        self.ui = {}
        # Milestone 15 (achievements) — whether the player has EVER entered
        # a revisit, for the "Looking Back" achievement. `self.revisiting`
        # only remembers whether one is in progress *right now*; once
        # exit_revisit() runs there is no other record it ever happened.
        # Monotonic by construction: only enter_revisit() ever sets this,
        # and it never sets it back to False.
        self.has_revisited = False
        # Milestone 6 — the ongoing log. Bootstrapped against whatever state
        # this Campaign starts with (population 6 and nothing researched,
        # for a brand-new game) so it only reports things that happen from
        # here on; `load_dict()` below re-bootstraps against the loaded
        # state instead when a save predates the log system, so an old save
        # doesn't retroactively dump the settlement's whole history into it.
        self.log = log.Chronicle()
        self.log.bootstrap(self.state, self.tree, self.tree.effects())

    # --- era progression ------------------------------------------------
    def record_era_snapshot(self, era=None, score=None):
        """Freezes how an era ended. Called when an era is completed."""
        era = era or self.state.era
        snapshot = snapshot_of(self.state, self.tree, score)
        self.era_snapshots[era] = snapshot
        return snapshot

    def advance_to_era(self, era):
        """Moves the campaign into a later era, snapshotting the one left.

        Phase 2's era-transition beat system will drive this; the save-side
        bookkeeping is built and tested now because that is the part that
        would be painful to retrofit.
        """
        if era not in sim.ERA_ORDER:
            return False
        if sim.era_index(era) <= sim.era_index(self.state.era):
            return False
        if self.revisiting is not None:
            return False

        self.record_era_snapshot(self.state.era)
        self.state.era = era
        self.tree.current_era = era
        if sim.era_index(era) > sim.era_index(self.furthest_era):
            self.furthest_era = era
        return True

    # --- revisiting ------------------------------------------------------
    def revisitable_eras(self):
        return [era for era in sim.ERA_ORDER if era in self.era_snapshots]

    def enter_revisit(self, era):
        """Loads a completed era's snapshot, parking forward progress."""
        # Phase 4 audit: validate against ERA_ORDER itself, not only against
        # era_snapshots' own keys. In ordinary play the two always agree
        # (record_era_snapshot() only ever keys by a real era), but
        # `era_snapshots` is also part of the save payload -- a hand-edited
        # save could hand this a bogus key that happens to collide with
        # something. Cheap, and it's the same source-of-truth cross-check
        # `load_dict()` already applies to `revisiting` itself below.
        if era not in sim.ERA_ORDER:
            return False
        if era not in self.era_snapshots:
            return False
        if self.revisiting is not None:
            return False

        self.parked_state = snapshot_of(self.state, self.tree)
        self.has_revisited = True
        _restore_snapshot(self.era_snapshots[era], self.state, self.tree)
        # Phase 4 audit: force the era explicitly rather than trusting
        # whatever the snapshot's own "era" field says. In ordinary play
        # they always agree (city_snapshot() always records the state's own
        # current era), but era_snapshots rides in the save payload too --
        # a hand-edited snapshot with a mismatched or invalid nested `era`
        # used to leave `state.era` reading whatever that field said (or,
        # since restore_city() now refuses an invalid one, whatever era the
        # state happened to be in before this call) instead of the era the
        # player actually asked to revisit. The era passed in here is the
        # one thing this method has already validated twice over (against
        # ERA_ORDER and against era_snapshots), so it's the one thing worth
        # trusting over the snapshot's own copy of it.
        self.state.era = era
        self.tree.current_era = era
        self.revisiting = era
        return True

    def exit_revisit(self):
        """Drops whatever happened during the revisit and returns to the arc.

        Deliberately discarding: a replay of a finished era is a look back,
        not a rewrite of it. The era's own snapshot is left untouched too.
        """
        if self.revisiting is None or self.parked_state is None:
            return False

        _restore_snapshot(self.parked_state, self.state, self.tree)
        # Phase 4 audit: same defensive force as enter_revisit() above, this
        # time against `furthest_era` -- the schema's own source of truth
        # for which era forward progress belongs to (state.era and
        # furthest_era always agree whenever the campaign isn't mid-revisit,
        # since advance_to_era() is the only thing that ever moves either
        # one forward). A tampered parked_state with a mismatched or
        # invalid `era` field can no longer strand the player somewhere
        # other than the era they were actually playing before the revisit.
        self.state.era = self.furthest_era
        self.tree.current_era = self.furthest_era
        self.parked_state = None
        self.revisiting = None
        return True

    # --- the save dict ---------------------------------------------------
    def to_dict(self):
        return {
            "save_version": SAVE_VERSION,
            "game": GAME_ID,
            "era_order": list(sim.ERA_ORDER),
            "current_era": self.state.era,
            "furthest_era": self.furthest_era,
            "revisiting": self.revisiting,
            "current_state": {
                "city": city_snapshot(self.state),
                "research": self.tree.snapshot(),
            },
            "parked_state": copy.deepcopy(self.parked_state),
            "era_snapshots": copy.deepcopy(self.era_snapshots),
            "ui": copy.deepcopy(self.ui),
            "log": self.log.snapshot(),
            "has_revisited": self.has_revisited,
        }

    def load_dict(self, data):
        """The exact inverse of `to_dict()`. False if the save isn't ours."""
        if not isinstance(data, dict):
            return False
        if data.get("game", GAME_ID) != GAME_ID:
            return False
        try:
            version = int(data.get("save_version", SAVE_VERSION))
        except (TypeError, ValueError):
            return False
        if version > SAVE_VERSION:
            # A save written by a newer build of the game. Refuse rather
            # than silently dropping whatever it knows that this build
            # doesn't.
            return False

        # The live half of the save gets the same type-guarding the parked
        # half and the snapshots already had: a truncated or hand-edited save
        # should load whatever it can, not take the page down on a TypeError
        # halfway through restoring.
        current = data.get("current_state")
        if not isinstance(current, dict):
            current = {}
        restore_city(self.state, current.get("city"))
        self.tree.restore(current.get("research"))

        era = data.get("current_era")
        if era in sim.ERA_ORDER:
            self.state.era = era
        self.tree.current_era = self.state.era

        furthest = data.get("furthest_era")
        self.furthest_era = furthest if furthest in sim.ERA_ORDER else self.state.era

        revisiting = data.get("revisiting")
        self.revisiting = revisiting if revisiting in sim.ERA_ORDER else None

        parked = data.get("parked_state")
        self.parked_state = copy.deepcopy(parked) if isinstance(parked, dict) else None
        if self.revisiting is not None and self.parked_state is None:
            # A revisit with nothing parked would strand the player in the
            # past; treat it as ordinary play in that era instead.
            self.revisiting = None

        snapshots = data.get("era_snapshots")
        self.era_snapshots = copy.deepcopy(snapshots) if isinstance(snapshots, dict) else {}
        if self.revisiting is not None and self.revisiting not in self.era_snapshots:
            # Belt-and-suspenders, purely defensive: `enter_revisit()` never
            # sets `revisiting` to an era without first confirming it has a
            # snapshot, so a well-formed save can't actually hit this. The
            # `parked_state`-is-missing guard above already catches a
            # hand-edited save that drops `parked_state` too, but not one
            # that keeps a (fabricated) `parked_state` while pointing
            # `revisiting` at an era `era_snapshots` never recorded — cross-
            # check against the schema's own source of truth rather than
            # trusting the save file's word for it. Clear `parked_state` too,
            # the same as the guard above does, so `revisiting is None`
            # keeps meaning "no forward progress parked" rather than leaving
            # it stranded with no `revisiting` era left to exit back from.
            self.revisiting = None
            self.parked_state = None

        ui = data.get("ui")
        self.ui = copy.deepcopy(ui) if isinstance(ui, dict) else {}

        # A save written before Milestone 6 has no "log" key at all -- rather
        # than restoring an empty Chronicle (which would then treat every
        # already-past population threshold and every already-researched
        # node as brand new the moment the player's next action re-checks
        # them), re-bootstrap against the state that was just restored above,
        # the same "old save, newer build" tolerance the rest of load_dict()
        # already gives every other field.
        log_data = data.get("log")
        if isinstance(log_data, dict):
            self.log.restore(log_data)
        else:
            self.log.bootstrap(self.state, self.tree, self.tree.effects())

        # Milestone 15 — a save written before this field existed simply
        # reads as "hasn't revisited yet", not an error; no backfill is
        # needed the way SOL's visited_bodies needed one; there is no
        # "mid-revisit but the flag says no" state any save this build
        # could have produced can be in, since `revisiting`/`has_revisited`
        # are set by the same code path from here on.
        self.has_revisited = bool(data.get("has_revisited", False))
        return True
