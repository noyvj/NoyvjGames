"""Continuum — the ongoing log: lightweight, milestone-triggered flavor text.

Milestone 6 of Phase 2. Per the design doc's Core system 4, this is short,
non-blocking, skippable prose tied to milestones within an era — a research
unlock, a population threshold, a livability shift — appended to a log the
player can glance at or ignore. It is deliberately never a popup or a
blocking prompt: `game.py` only ever appends to a visible panel, it never
interrupts input.

**This is also where feedback now lives**, per the doc's own framing
(replacing the climate quartet's end-of-session survey prompts): a
livability shift produces a log entry reacting to it in the settlement's
own voice — "word travels fast when people go hungry" rather than "did
this feel effective?". `_livability_shift_entry()` below is that seam.
Prose is deliberately generic/editable for now, per the doc's own note to
"build the system first, refine prose during a dedicated pass" — nothing
here is final copy.

Three trigger conditions, matching the doc's own milestone description
exactly:

- **Research unlock** — fires the moment a node is researched (not tied to
  season advance, since research can happen mid-season).
- **Population threshold** — fires when population crosses one of
  `POPULATION_MILESTONES` for the first time. Loosely inspired by Dunbar's
  layered group-size thresholds (~5/15/50/150) that
  `continuum-real-world-sources.md`'s Tribal sources cite for real
  population/social-structure dynamics — not literal Dunbar numbers, but
  the same idea that certain sizes change a settlement's *character*, not
  just its number.
- **Livability shift** — fires when `sustainability.score_label()` changes
  between one season and the next. An upward shift gets a generic
  improvement line; a downward shift's line is chosen by whichever
  component is currently weakest, so the log names roughly *what* got
  worse rather than only *that* something did.

`Chronicle` is deliberately its own object rather than living on
`CityState` or `ResearchTree`: it is the one place "has this already been
logged" bookkeeping lives, and keeping it out of `sim.py`/`research.py`
keeps those free of anything to do with narration — the same separation
of concerns the rest of Phase 1 set up. `save.py`'s `Campaign` owns one
`Chronicle` alongside its `CityState` and `ResearchTree`, and Milestone 7's
era-transition beat system is expected to add a `"transition"` kind here
by calling into `Chronicle` from `Campaign.advance_to_era()`.
"""

import sustainability

# --- population thresholds ----------------------------------------------
POPULATION_MILESTONES = [10, 15, 25, 40, 60, 100, 150]

POPULATION_MILESTONE_TEXT = {
    10: "The settlement has grown past ten. Faces that used to be familiar to everyone now need introducing.",
    15: "Fifteen now call this place home — small enough still to remember every name, most days.",
    25: "Twenty-five. The settlement has outgrown the size a handful of people can hold together by memory alone.",
    40: "Forty. Whatever keeps everyone fed and sheltered this long is no longer a matter of luck.",
    60: "Sixty. This is no longer a handful of families — it is something closer to a town.",
    100: "A hundred people live here now. However this got built, it wasn't an accident.",
    # Milestone 13 — literally Dunbar's own number, the same layer the
    # Tribal info panel's sources have cited since the very first era: the
    # point past which no single mind can hold everyone else in memory at
    # all, stable-relationship or otherwise. Fitting as the last threshold
    # this table needs: the settlement that crosses it is, by the time it
    # does, already off-world.
    150: "One hundred fifty. Long before any of this left the ground, that was already the number past which no one person could hold everyone else in mind at once.",
}

# --- livability shifts (the diegetic feedback seam) ----------------------
# Keyed by sustainability.score_label()'s exact (capitalised) return
# values, not lower-cased -- keeping the two in the same case throughout
# avoids a silent mismatch between what gets stored in a save and what
# `_LABEL_ORDER` below recognises as valid.
LIVABILITY_UP_TEXT = {
    "Failing": "Whatever was at its worst has eased, at least a little.",
    "Strained": "It isn't comfortable here, but it isn't unraveling either.",
    "Steady": "Things have settled. Whatever was wrong before is, for now, being managed.",
    "Thriving": "By any measure that matters here, this is a good place to live right now.",
}

# Keyed by sustainability.weakest_component()'s component ids, which are
# already lower-case (see sustainability.COMPONENTS) -- no case mismatch
# risk here the way there is for the score-label keys above.
LIVABILITY_DOWN_TEXT = {
    "livability": "Word travels fast when people go hungry, or without a roof. It's traveling now.",
    "equity": "Not everyone here is living the same life. That's starting to be said out loud.",
    "balance": "The land is giving less than it used to. People have started to notice.",
    "resilience": "Nothing is set aside for a bad season anymore. Everyone can feel how thin that is.",
}

_GENERIC_UP = "Things are, on the whole, a little better than they were."
_GENERIC_DOWN = "Something here has gotten harder. It hasn't gone unnoticed."

# The same shared band ordering sustainability.score_label() returns —
# kept as one alias here rather than a second hand-copied list, after an
# earlier hand-copied (and mistakenly lower-cased) version of this list
# caused a save/restore bug caught in testing (see CLAUDE.md's Milestone 6
# build notes).
_LABEL_ORDER = sustainability.SCORE_LABELS


def _label_rank(label):
    return _LABEL_ORDER.index(label) if label in _LABEL_ORDER else 0


class LogEntry:
    """One line of flavor text, stamped with when it happened."""

    def __init__(self, season, era, kind, text):
        self.season = season
        self.era = era
        self.kind = kind
        self.text = text

    def to_dict(self):
        return {"season": self.season, "era": self.era, "kind": self.kind, "text": self.text}

    @staticmethod
    def from_dict(data):
        if not isinstance(data, dict):
            return None
        text = data.get("text")
        if not text:
            return None
        return LogEntry(
            data.get("season", 0),
            data.get("era", ""),
            data.get("kind", "beat"),
            text,
        )


def _livability_shift_entry(season, era, old_label, new_label, weakest):
    if _label_rank(new_label) > _label_rank(old_label):
        text = LIVABILITY_UP_TEXT.get(new_label, _GENERIC_UP)
        kind = "livability-up"
    else:
        text = LIVABILITY_DOWN_TEXT.get(weakest, _GENERIC_DOWN)
        kind = "livability-down"
    return LogEntry(season, era, kind, text)


# A session-length cap, not a design limit -- oldest entries drop first so
# a very long play session doesn't grow the save file without bound.
MAX_ENTRIES = 60


class Chronicle:
    """Owns the visible log and the "have we already logged this" state
    behind it. One Chronicle per Campaign, spanning the whole playthrough
    (it is not reset or swapped during an era revisit — see save.py)."""

    def __init__(self):
        self.entries = []
        self._population_milestones_hit = set()
        self._last_score_label = None
        self._researched_seen = set()

    def bootstrap(self, state, tree, effects):
        """Captures a baseline without logging anything.

        Called once for a brand-new campaign (so starting at population 6
        doesn't retroactively "discover" milestone 10 doesn't apply, and a
        fresh tree has nothing researched to report), and again for a save
        written before this Chronicle existed (see `save.Campaign.
        load_dict`) so loading it doesn't dump the settlement's entire
        history into the log as if it all just happened.
        """
        self._researched_seen = set(tree.researched)
        self._population_milestones_hit = {
            m for m in POPULATION_MILESTONES if state.population >= m
        }
        self._last_score_label = sustainability.score_label(
            sustainability.score(state, effects), sustainability.is_hard_mode(state)
        )

    def _add(self, entry):
        self.entries.append(entry)
        if len(self.entries) > MAX_ENTRIES:
            self.entries = self.entries[-MAX_ENTRIES:]

    # --- triggers ---------------------------------------------------------
    def check_research(self, state, tree):
        """Call right after a research attempt, successful or not."""
        newly = [nid for nid in tree.researched if nid not in self._researched_seen]
        for node_id in newly:
            node = tree.nodes[node_id]
            self._add(LogEntry(state.season, state.era, "research", f"Discovery: {node.name}. {node.blurb}"))
            self._researched_seen.add(node_id)

    def check_population(self, state):
        """Call once per completed season."""
        for milestone in POPULATION_MILESTONES:
            if state.population >= milestone and milestone not in self._population_milestones_hit:
                self._population_milestones_hit.add(milestone)
                self._add(
                    LogEntry(
                        state.season,
                        state.era,
                        "population",
                        POPULATION_MILESTONE_TEXT[milestone],
                    )
                )

    def check_livability(self, state, effects):
        """Call once per completed season, after `check_population`."""
        label = sustainability.score_label(
            sustainability.score(state, effects), sustainability.is_hard_mode(state)
        )
        if self._last_score_label is not None and label != self._last_score_label:
            weakest = sustainability.weakest_component(state, effects)
            self._add(
                _livability_shift_entry(state.season, state.era, self._last_score_label, label, weakest)
            )
        self._last_score_label = label

    def log_transition(self, season, era, text):
        """Appends a transition-beat entry (Milestone 7's `transition.py`
        is the one caller outside this module — check_research()/
        check_population()/check_livability() above stay this module's own
        triggers, but a transition beat is decided by transition.py's own
        readiness rules, not by anything Chronicle tracks itself)."""
        self._add(LogEntry(season, era, "transition", text))

    # --- save support -------------------------------------------------------
    def snapshot(self):
        return {
            "entries": [e.to_dict() for e in self.entries],
            "population_milestones_hit": sorted(self._population_milestones_hit),
            "last_score_label": self._last_score_label,
            "researched_seen": sorted(self._researched_seen),
        }

    def restore(self, data):
        """Tolerates a missing/malformed dict the same way save.py's other
        restore paths do — a truncated save should load whatever it can.

        Phase 4 audit: `researched_seen` used to be handed straight to
        `set(...)` — a real node id is always a string (hashable), but a
        hand-edited save putting a dict or a list in that list instead blew
        up with an unhashable-type TypeError before this entry was ever
        inspected. Filtered to strings first (same "only trust the shape
        this field can legitimately have" discipline `research.py`'s own
        `restore()` already applies to its `researched` list) so a bad
        entry is dropped instead of crashing the whole restore.
        """
        if not isinstance(data, dict):
            data = {}

        entries = data.get("entries")
        self.entries = (
            [e for e in (LogEntry.from_dict(d) for d in entries) if e is not None]
            if isinstance(entries, list)
            else []
        )

        milestones = data.get("population_milestones_hit")
        self._population_milestones_hit = (
            {m for m in milestones if m in POPULATION_MILESTONES}
            if isinstance(milestones, list)
            else set()
        )

        label = data.get("last_score_label")
        self._last_score_label = label if label in _LABEL_ORDER else None

        researched = data.get("researched_seen")
        self._researched_seen = (
            {nid for nid in researched if isinstance(nid, str)}
            if isinstance(researched, list)
            else set()
        )
