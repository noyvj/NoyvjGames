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
      "ui":             {...}           # view toggles worth preserving
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

import sim
import sustainability

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
    "fed_fraction",
    "last_extraction",
    "last_sustainable_yield",
    "last_report",
    "score_history",
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


def city_snapshot(state):
    """A deep-copied, JSON-safe record of one CityState."""
    return {field: copy.deepcopy(getattr(state, field)) for field in CITY_FIELDS}


def restore_city(state, data):
    """Writes a city snapshot back into an existing CityState, in place.

    Missing fields keep their current value, so a save written before a
    field existed still loads — and, per CITY_KEYED_DICTS, that holds one
    level down as well.
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
                for key in live:
                    if key in value:
                        live[key] = copy.deepcopy(value[key])
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
        if era not in self.era_snapshots:
            return False
        if self.revisiting is not None:
            return False

        self.parked_state = snapshot_of(self.state, self.tree)
        _restore_snapshot(self.era_snapshots[era], self.state, self.tree)
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

        ui = data.get("ui")
        self.ui = copy.deepcopy(ui) if isinstance(ui, dict) else {}
        return True
