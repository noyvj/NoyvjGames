"""Aftermath — Climate Adaptation & Resilience Game.

Runs in-browser via Pyodide. A repeated-short-run core loop: a fixed
schedule of extreme weather (and other resilience-relevant) events,
resource allocation between events (resilience vs. growth investment),
and damage resolution, feeding a persistent cross-run skill tree and
"how far you've come" run comparison. See CLAUDE.md for the full
milestone history.
"""

import math
import copy
import json
import time

import export_progress
import info_page
import run_code as shared_run_code
import seed as shared_seed
from js import document, localStorage, setTimeout
from pyodide.ffi import create_proxy

STARTING_RESOURCES = 200.0

RESILIENCE_COST = 25
GROWTH_COST = 20
GROWTH_INCOME_PER_UNIT = 8

RESILIENCE_MITIGATION_PER_UNIT = 0.05
MAX_MITIGATION = 0.85

# Fixed schedule — every run faces the same sequence of event types, so
# runs are comparable to each other (needed for Milestone 5's "how far
# you've come" comparison). Iteration Pass 2 extended this with two
# non-weather resilience shocks (supply-chain, infrastructure) so
# "resilience" reads as a broader societal capacity than storm-proofing
# alone — same scheduled-event structure, just more event variety.
# E6 (planning/TODO.md per-game backlog) added a third event category —
# "social" — represented by a single new event type, civil_unrest, which
# replaces the schedule's second "storm" slot rather than extending the
# schedule's length: test_iteration_pass_2.py's "schedule index 2 is
# supply_chain" and first-two-events-unchanged assertions both depend on
# the front of this list staying exactly as it was, and keeping the
# length at 7 (instead of appending an 8th event) avoids re-litigating
# the fixed total-damage-vs-starting-resources balance the existing
# hope-angle/skill-tree tests are tuned against.
EVENT_SCHEDULE = [
    "flood", "heatwave", "supply_chain", "storm", "infrastructure_failure", "flood", "civil_unrest",
]

# E17a: climate scenario pack -- alternate event schedules grounded in the
# hazards different kinds of place actually face, chosen when a run starts.
# Every schedule keeps the length at 7 and a total base damage within roughly
# 10% of the classic run's 265 (the classic schedule is a mix of all three
# kinds), so the fixed damage-vs-starting-resources balance the skill-tree
# tests are tuned against still holds; only WHICH shocks arrive, and in what
# order, changes. "classic" is the original schedule and the default.
SCENARIOS = {
    "classic": {
        "label": "Classic mix",
        "blurb": "The original run: a bit of everything.",
        "schedule": EVENT_SCHEDULE,
    },
    "coastal": {
        "label": "Coastal",
        "blurb": "Storm surge and flooding dominate; less of the inland grind.",
        "schedule": ["flood", "storm", "heatwave", "flood", "supply_chain", "storm", "civil_unrest"],
    },
    "inland": {
        "label": "Inland",
        "blurb": "Long heat and broken supply lines rather than water.",
        "schedule": ["heatwave", "supply_chain", "infrastructure_failure", "heatwave", "storm", "flood", "civil_unrest"],
    },
    "urban": {
        "label": "Urban",
        "blurb": "Dense systems: failing infrastructure, strained supply and social unrest.",
        "schedule": ["infrastructure_failure", "supply_chain", "civil_unrest", "heatwave", "infrastructure_failure", "flood", "civil_unrest"],
    },
    # E17b: named real places. The game only has six event types, so each
    # place is a deliberately simplified mapping of its best-known hazards
    # onto them (e.g. earthquake and wildfire damage read as infrastructure
    # failure and heat; winter storms count as storms), not a forecast. Same
    # rules as above: 7 events, total base damage within ~12% of Classic.
    "san_francisco": {
        "label": "San Francisco",
        "blurb": "Earthquake and wildfire risk (infrastructure failure, fire-season heat, supply breaks), atmospheric-river flooding, and almost no hurricanes or snow.",
        "schedule": ["infrastructure_failure", "heatwave", "infrastructure_failure", "supply_chain", "heatwave", "infrastructure_failure", "flood"],
    },
    "houston": {
        "label": "Houston",
        "blurb": "Hurricanes and flooding first, then heat and strained infrastructure.",
        "schedule": ["storm", "flood", "storm", "flood", "heatwave", "infrastructure_failure", "supply_chain"],
    },
    "phoenix": {
        "label": "Phoenix",
        "blurb": "Extreme desert heat that wears down power and supply, with rare but sharp flash floods.",
        "schedule": ["heatwave", "infrastructure_failure", "heatwave", "supply_chain", "heatwave", "flood", "civil_unrest"],
    },
    "chicago": {
        "label": "Chicago",
        "blurb": "Severe storms and winter storms, summer heat, flooding and a stressed supply network.",
        "schedule": ["storm", "heatwave", "infrastructure_failure", "flood", "storm", "supply_chain", "civil_unrest"],
    },
    # FY-3: the fourth event category, "health", arrives only through this
    # selectable scenario. The Classic mix above is deliberately untouched:
    # it is the fixed baseline the run-1-versus-latest comparison, the
    # hope-angle tests and every saved run were built against. Total base
    # damage 247 against Classic's 265 (inside the usual 12% band).
    "heat_season": {
        "label": "Heat season",
        "blurb": "A long hot summer: heatwaves, power and supply strain, and two heat-health emergencies where the heat itself endangers people (a new kind of shock).",
        "schedule": ["heatwave", "heat_mortality", "supply_chain", "infrastructure_failure", "heat_mortality", "flood", "civil_unrest"],
    },
}
DEFAULT_SCENARIO = "classic"

EVENT_LABEL = {
    "flood": "Flood",
    "heatwave": "Heatwave",
    "storm": "Storm",
    "supply_chain": "Supply-Chain Disruption",
    "infrastructure_failure": "Infrastructure Failure",
    "civil_unrest": "Civil Unrest",
    # FY-3: the health category's first event type.
    "heat_mortality": "Heat-Health Emergency",
}

# The original six event types. The Seen It All achievement (codex_complete)
# is defined on exactly these, so adding event types later can never take an
# earned achievement away; a newer type gets its own achievement instead.
CODEX_CORE_TYPES = ("flood", "heatwave", "storm", "supply_chain", "infrastructure_failure", "civil_unrest")

EVENT_ICON = {
    # Each icon carries an explicit U+FE0F variation selector so every
    # entry renders as a colorful emoji glyph consistently across
    # platforms/fonts, rather than some (e.g. the high-voltage sign) risking
    # a plain monochrome text-style glyph without it. Purely cosmetic —
    # rendering-only, no functional effect.
    "flood": "\U0001F30A️",  # water wave
    "heatwave": "\U0001F525️",  # fire
    "storm": "\U0001F32A️",  # tornado
    "supply_chain": "\U0001F4E6️",  # package
    "infrastructure_failure": "⚡️",  # high voltage
    "civil_unrest": "\U0001F4E2️",  # loudspeaker
    "heat_mortality": "\U0001F321️",  # thermometer
}

EVENT_BASE_DAMAGE = {
    "flood": 40.0,
    "heatwave": 35.0,
    "storm": 50.0,
    "supply_chain": 30.0,
    "infrastructure_failure": 38.0,
    "civil_unrest": 32.0,
    "heat_mortality": 36.0,
}

# Iteration Pass 2 — event-type category, so weather and non-weather
# shocks get a distinct visual/audio signature (a CSS class here, since
# there's no audio system in the stack) rather than just a different
# label on the same event UI.
EVENT_CATEGORY = {
    "flood": "weather",
    "heatwave": "weather",
    "storm": "weather",
    "supply_chain": "non-weather",
    "infrastructure_failure": "non-weather",
    # E6: a third category — social shocks — distinct from both physical
    # weather and physical/economic infrastructure disruption. Civil
    # unrest (protest, strikes, breakdowns in community cooperation) is a
    # real, documented consequence of repeated disaster strain, and
    # belongs in "resilience-relevant shocks" alongside the other two.
    "civil_unrest": "social",
    # FY-3: a fourth category -- health shocks, where the hazard (here, heat)
    # harms people directly rather than damaging places or supply lines.
    # The skill tree has no specialization for it, so its only dedicated
    # protection is an earned societal memory (like non-weather shocks).
    "heat_mortality": "health",
}

# GE-15: Flawless Defense. An event whose final damage is at most this share
# of its base (unscaled) damage counts as flawless: +1 knowledge point at the
# end of the run and a lifetime achievement. Mitigation is capped at 85%, so
# 15% is exactly "held at the cap against a typical or milder event"; the
# 10% in the original idea was unreachable (an 85% cap against even a 0.85x
# event still lets 12.75% through), so the line sits where the cap puts it.
FLAWLESS_DAMAGE_FRACTION = 0.15
FLAWLESS_BONUS_KNOWLEDGE = 1

# GE-13: an event counts as "held" for the prevented-damage streak when the
# settlement prevented at least this share of the damage it would otherwise
# have taken.
HELD_PREVENTED_FRACTION = 0.5

# Iteration-pass addition: severity varies per event so repeated runs
# don't feel identical. Deterministic (a hash-based formula, not
# wall-clock random) rather than truly random, and off entirely for
# run 1 — this keeps the run-1-vs-latest-run comparison
# (progress_comparison) meaningful (same run number always faces the
# same challenge level) and keeps every single-run test's exact damage
# numbers unchanged.
SEVERITY_VARIATION_MIN = 0.85
SEVERITY_VARIATION_MAX = 1.15

# Iteration Pass 3 (fun/teaching-balance) — a skill tree that only makes
# the player stronger while events stay flat is the textbook
# flow-boredom failure mode, so the severity spread widens symmetrically
# around the same 1.0 center for each resilience skill the player has
# unlocked overall. Center stays fixed (this isn't "the game punishes
# you for upgrading" — the hope-angle comparison must stay meaningful),
# but the ceiling a stronger skill tree can face rises right along with
# the floor it can catch, so a fully-invested run still gets asked
# something a first run never sees, instead of becoming a rote replay
# of an already-solved strategy.
SEVERITY_VARIATION_RANGE_PER_SKILL = 0.05


# ---------------------------------------------------------------------------
# E-30: save health. Every write to the browser's localStorage goes through
# _storage_write(), which remembers when the last write succeeded and which
# keys failed (a full or blocked store throws), so the badge can say "Saved 12s
# ago", "Not saved: storage full or blocked" or "Unsaved changes" truthfully.
# ---------------------------------------------------------------------------
STORAGE_PROBE_KEY = "aftermath_storage_probe"
_storage_state = {"last_ok": None, "failed": {}}


def _now():
    """Seconds since the epoch (tests replace this to move the clock)."""
    return time.time()


def _storage_write(key, value):
    """localStorage.setItem that never raises: returns True when the write went through."""
    try:
        localStorage.setItem(key, value)
    except Exception as error:  # a JsException (quota or blocked) in Pyodide; any error here means "not saved"
        _storage_state["failed"][key] = str(error)[:120] or "storage error"
        return False
    _storage_state["failed"].pop(key, None)
    _storage_state["last_ok"] = _now()
    return True


def probe_storage():
    """Tries a tiny write and delete. A failure is remembered under STORAGE_PROBE_KEY and cleared
    again by the next probe that works, so the badge recovers after space is freed."""
    try:
        localStorage.setItem(STORAGE_PROBE_KEY, "1")
        localStorage.removeItem(STORAGE_PROBE_KEY)
    except Exception as error:
        _storage_state["failed"][STORAGE_PROBE_KEY] = str(error)[:120] or "storage error"
        return False
    _storage_state["failed"].pop(STORAGE_PROBE_KEY, None)
    return True


def format_age(seconds):
    """'just now', '12s ago', '3 min ago', '2 h ago' (ui.js keeps the same wording while the page is open)."""
    seconds = max(0, int(seconds))
    if seconds < 5:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    return f"{seconds // 3600} h ago"


def _read_json(key):
    """(found, value): the parsed stored JSON, (False, None) when absent, (None, None) when unreadable."""
    try:
        raw = localStorage.getItem(key)
    except Exception:
        return None, None
    if not raw:
        return False, None
    try:
        return True, json.loads(raw)
    except ValueError:
        return None, None


def unsaved_progress():
    """Which kinds of progress in memory differ from what the browser has stored. Normally empty:
    every change is written at once. Not empty if the stored copy was cleared or replaced from outside
    (another tab, browser tools, storage eviction) or a write silently did not stick."""
    problems = []
    found, stored = _read_json(SKILL_TREE_STORAGE_KEY)
    mine = skill_tree.to_dict()
    if found is None:
        problems.append("skill tree")
    elif found and (
        not isinstance(stored, dict)
        or stored.get("knowledge_points", 0) != mine["knowledge_points"]
        or sorted(stored.get("unlocked", [])) != mine["unlocked"]
    ):
        problems.append("skill tree")
    elif not found and (mine["knowledge_points"] or mine["unlocked"]):
        problems.append("skill tree")
    found, stored = _read_json(RUN_HISTORY_STORAGE_KEY)
    if found is None or (found and stored != run_history) or (not found and run_history):
        problems.append("run history")
    found, stored = _read_json(META_STORAGE_KEY)
    if found is None or (found and _sanitize_meta(stored) != meta) or (not found and meta != _default_meta()):
        problems.append("settlement notes and presets")
    return problems


def storage_health():
    """(state, text): state is 'failed', 'unsaved', 'saved' or 'ready'."""
    if _storage_state["failed"]:
        if STORAGE_PROBE_KEY in _storage_state["failed"]:
            probe_storage()  # space may have been freed since
        if _storage_state["failed"]:
            return "failed", (
                "\u26a0 Not saved: this browser's storage is full or blocked, so new progress is only "
                "kept until you close the page. Export your progress now."
            )
    problems = unsaved_progress()
    if problems:
        return "unsaved", (
            "\u26a0 Unsaved changes: your " + ", ".join(problems) + " on this page differ from what this browser has "
            "stored. Export your progress to be safe."
        )
    last = _storage_state["last_ok"]
    if last is None:
        return "ready", "\u2713 Progress saves to this browser automatically."
    return "saved", f"\u2713 Saved {format_age(_now() - last)}"


def skill_tree_strength():
    """How many resilience skills are unlocked overall — the signal Pass
    3 uses to widen event-severity variation so a stronger skill tree
    keeps facing a wider spread of challenge, not a flat one."""
    return len(skill_tree.unlocked)


# E7: a proper difficulty-scaling curve across many runs -- beyond the
# per-skill widening above, the severity spread also grows slowly with the
# number of runs the player has completed over the settlement's lifetime,
# capped so a very long career can't run away. The center stays 1.0, same
# hope-angle reasoning as SEVERITY_VARIATION_RANGE_PER_SKILL.
SEVERITY_VARIATION_RANGE_PER_LIFETIME_RUN = 0.004
SEVERITY_LIFETIME_RANGE_CAP = 0.06


def lifetime_severity_widening(lifetime_runs=None):
    if lifetime_runs is None:
        lifetime_runs = len(run_history)
    return min(SEVERITY_LIFETIME_RANGE_CAP, SEVERITY_VARIATION_RANGE_PER_LIFETIME_RUN * max(0, lifetime_runs))


def severity_bounds(skill_strength=0, lifetime_runs=None):
    """(min, max) of the severity multiplier for run 2 onward at this
    skill level / career length -- shared by event_severity() and the
    E14/E20 range and tooltip displays so they can never drift apart."""
    center = (SEVERITY_VARIATION_MIN + SEVERITY_VARIATION_MAX) / 2
    half_width = (SEVERITY_VARIATION_MAX - SEVERITY_VARIATION_MIN) / 2
    half_width += SEVERITY_VARIATION_RANGE_PER_SKILL * skill_strength
    half_width += lifetime_severity_widening(lifetime_runs)
    return center - half_width, center + half_width


def event_severity(run_number, event_index, skill_strength=0, lifetime_runs=None):
    if run_number <= 1:
        return 1.0
    seed = (run_number * 97 + event_index * 31) % 100
    variation_min, variation_max = severity_bounds(skill_strength, lifetime_runs)
    return variation_min + (seed / 100) * (variation_max - variation_min)


def severity_label(severity):
    if severity < 0.95:
        return "mild"
    if severity > 1.05:
        return "severe"
    return "typical"


# ---------------------------------------------------------------------------
# Per-event derivations. Everything below is a pure function of one event_log
# entry ({"type", "damage", "severity"}): the unmitigated damage is the base
# damage times the severity, so what was prevented, the mitigation that held
# and whether the defense was flawless can all be recovered from the entries
# already stored in run_log_history, without a new saved field (older logs
# included).
# ---------------------------------------------------------------------------
def entry_unmitigated(entry):
    return EVENT_BASE_DAMAGE.get(entry.get("type"), 0.0) * entry.get("severity", 1.0)


def entry_prevented(entry):
    return max(0.0, entry_unmitigated(entry) - entry.get("damage", 0.0))


def entry_mitigation(entry):
    """Share of the unmitigated damage that was prevented (0..1), or None
    for an entry of an unknown type."""
    unmitigated = entry_unmitigated(entry)
    if unmitigated <= 0:
        return None
    return min(1.0, entry_prevented(entry) / unmitigated)


def entry_is_flawless(entry):
    """GE-15: damage held to FLAWLESS_DAMAGE_FRACTION of the event's base."""
    base = EVENT_BASE_DAMAGE.get(entry.get("type"))
    if base is None:
        return False
    return entry.get("damage", base) <= base * FLAWLESS_DAMAGE_FRACTION + 1e-9


def flawless_count(event_log):
    return sum(1 for entry in event_log if entry_is_flawless(entry))


def held_streak(event_log):
    """GE-13: how many of the most recent events in a row prevented at least
    HELD_PREVENTED_FRACTION of their unmitigated damage."""
    streak = 0
    for entry in reversed(event_log):
        mitigation = entry_mitigation(entry)
        if mitigation is None or mitigation + 1e-9 < HELD_PREVENTED_FRACTION:
            break
        streak += 1
    return streak


def adjusted_score(score, event_log):
    """E-9: the score as if every event had struck at the typical 1.00x
    severity. Each event's damage divided by its severity is what it would
    have cost at 1.00x, so the adjustment is the sum of damage x (1 - 1/severity):
    positive when the draws were harsher than typical (the run is credited for
    that), negative when they were gentler. It uses only the stored
    event_log entries (type, damage, severity), so every logged run can be
    adjusted, and the severity already contains the skill-strength and
    lifetime widening, so those are normalised away too. Never below zero."""
    extra = 0.0
    for entry in event_log or []:
        if not isinstance(entry, dict):
            continue
        severity = entry.get("severity", 1.0)
        if isinstance(severity, (int, float)) and severity > 0:
            extra += entry.get("damage", 0.0) * (1.0 - 1.0 / severity)
    return max(0.0, score + extra)


def adjusted_text(score, event_log):
    """'adjusted 134 for 1.08x average severity' (E-9), the same words wherever it is shown."""
    if not event_log:
        return f"adjusted {score:.0f}"
    average = sum(e.get("severity", 1.0) for e in event_log) / len(event_log)
    return f"adjusted {adjusted_score(score, event_log):.0f} for {average:.2f}\u00d7 average severity"


# Skill tree — lives outside the run loop entirely, persisting between
# runs (and between visits, via localStorage). Bonus application to new
# runs is Milestone 4's job; this milestone is just the structure.
#
# E2/E3 (planning/TODO.md's per-game backlog) added a fourth and fifth
# node plus a "prereqs" list on every entry (empty for the original
# three, which stay unlockable from the start). mutual_aid_network is
# the first skill that actually requires prereqs -- deliberately built
# on top of both foundational skills, since a mutual-aid network only
# functions once a settlement already has both physical infrastructure
# and pooled resources to organize around.
SKILLS = {
    "reinforced_infrastructure": {
        "cost": 3,
        "prereqs": [],
        "label": "Reinforced Infrastructure",
        "description": "+2 starting resilience capacity",
        "real_practice": "Mirrors real building codes requiring flood-resistant foundations and reinforced structures in vulnerable regions.",
    },
    "community_reserves": {
        "cost": 3,
        "prereqs": [],
        "label": "Community Reserves",
        "description": "+50 starting resources",
        "real_practice": "Mirrors community emergency funds and mutual-aid reserves, letting a region self-fund early recovery instead of waiting on outside aid.",
    },
    "early_warning": {
        "cost": 5,
        "prereqs": [],
        "label": "Early Warning Systems",
        "description": "+10% mitigation on all events",
        "real_practice": "Mirrors real early-warning networks — alert systems for floods and storms have been shown to cut disaster damage and casualties dramatically for relatively low cost.",
    },
    "adaptive_growth": {
        "cost": 4,
        "prereqs": [],
        "label": "Adaptive Growth Practices",
        "description": "+1 starting growth capacity",
        "real_practice": "Mirrors diversified local economies that keep some productive capacity running even while a region's resilience investment is still catching up.",
    },
    "mutual_aid_network": {
        "cost": 6,
        "prereqs": ["reinforced_infrastructure", "community_reserves"],
        "label": "Mutual Aid Network",
        "description": "+5% mitigation on all events (stacks with Resilience investment)",
        "real_practice": "Mirrors real mutual-aid networks, which only function once a settlement already has both physical infrastructure and pooled resources to organize around — neighbors sharing tools, shelter, and labor during recovery.",
    },
    # E1/E3: a sixth and seventh node -- the tree branches after its
    # foundations into two specialization paths. Weather-focused
    # (climate_hardening) builds on the physical/early-warning side;
    # social-shock-focused (civic_preparedness) builds on the pooled-
    # resources side and gives Civil Unrest its own upgrade path. Each
    # only reduces damage from its own event category, so choosing
    # between them (or paying for both) is a genuine allocation decision.
    "civic_preparedness": {
        "cost": 5,
        "prereqs": ["community_reserves"],
        "branch": "social",
        "label": "Civic Preparedness",
        "description": "-35% damage from social-shock events (Civil Unrest)",
        "real_practice": "Mirrors community-resilience programs — trusted local institutions, neighborhood councils, and conflict-mediation training — that keep cooperation intact when disaster strain would otherwise fray it.",
    },
    "climate_hardening": {
        "cost": 6,
        "prereqs": ["reinforced_infrastructure", "early_warning"],
        "branch": "weather",
        "label": "Climate Hardening",
        "description": "-20% damage from weather events (Flood, Heatwave, Storm)",
        "real_practice": "Mirrors retrofit programs — raised foundations, cool roofs, storm-rated grids — layered on top of warning systems so the same alert buys far more protection.",
    },
}

SKILL_TREE_STORAGE_KEY = "aftermath_skill_tree_v1"
RUN_HISTORY_STORAGE_KEY = "aftermath_run_history_v1"

# Iteration Pass 2 — legacy system (stretch goal, built after the
# diversified events were solid): each completed run leaves behind a
# small trace beyond the skill-tree currency — a persistent record of
# which event types this settlement has weathered before, referenced as
# flavor text in the next run rather than a mechanical bonus.
LEGACY_STORAGE_KEY = "aftermath_legacy_events_v1"
# E4/E7 (planning/TODO.md per-game backlog): additive persistence
# alongside the two keys above, not a replacement for either.
LEGACY_COUNTS_STORAGE_KEY = "aftermath_legacy_event_counts_v1"
RUN_LOG_HISTORY_STORAGE_KEY = "aftermath_run_log_history_v1"

# The shared save widget can restore an *older* in-memory RunState over a
# newer one (that's the whole point of "load a save from earlier") --
# including one whose event_index has already advanced past a point that
# was, in a different RunState object, resolved all the way to completion
# and already awarded knowledge/history/legacy. Without a persistent
# record of which run_number has already paid out, re-resolving that
# reloaded run's remaining events to completion would trigger the
# completion payout a second time for the same run: free knowledge
# points and a duplicate run_history entry, just by reloading a save
# taken before the run's last event. This tracks the highest run_number
# that has already been awarded (independent of any one RunState
# instance) so a completion only pays out the first time a given
# run_number crosses the finish line, no matter how many stale snapshots
# of it get loaded and re-resolved afterward.
AWARDED_RUN_STORAGE_KEY = "aftermath_highest_awarded_run_v1"


def load_highest_awarded_run():
    raw = localStorage.getItem(AWARDED_RUN_STORAGE_KEY)
    if not raw:
        return 0
    try:
        return int(json.loads(raw))
    except (ValueError, TypeError):
        return 0


def save_highest_awarded_run(run_number):
    _storage_write(AWARDED_RUN_STORAGE_KEY, json.dumps(run_number))


def load_legacy_events():
    raw = localStorage.getItem(LEGACY_STORAGE_KEY)
    if not raw:
        return set()
    try:
        return set(json.loads(raw))
    except ValueError:
        return set()


def save_legacy_events(events):
    _storage_write(LEGACY_STORAGE_KEY, json.dumps(sorted(events)))


# E29: societal memory. A settlement that comes through a run in ruins does
# not forget: the category of shock that did the most damage in that run
# leaves a permanent, unique defence (the memory of what went wrong). It is
# not a purchase and cannot be bought otherwise: a non-weather category
# (supply chain, infrastructure) has no specialization in the skill tree at
# all, so its memory is the only dedicated protection it can ever get and is
# the strongest; a weather or social memory is smaller because the tree already
# offers those. Kept per browser like the skill tree, and only formed by a run
# that ends at or below VERY_BAD_RUN_SCORE, so a rough-but-alive run never
# triggers it.
SOCIETAL_MEMORY_STORAGE_KEY = "aftermath_societal_memory_v1"
VERY_BAD_RUN_SCORE = 10.0
SOCIETAL_MEMORY_BONUS = {"weather": 0.15, "social": 0.15, "non-weather": 0.25, "health": 0.25}
SOCIETAL_MEMORY_LABEL = {
    "weather": "the weather that broke it",
    "social": "the unrest that broke it",
    "non-weather": "the systems failure that broke it",
    "health": "the health emergency that broke it",
}


def load_societal_memory():
    raw = localStorage.getItem(SOCIETAL_MEMORY_STORAGE_KEY)
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except ValueError:
        return set()
    if not isinstance(data, list):
        return set()
    return {c for c in data if isinstance(c, str) and c in SOCIETAL_MEMORY_BONUS}


def save_societal_memory(categories):
    _storage_write(SOCIETAL_MEMORY_STORAGE_KEY, json.dumps(sorted(categories)))


# E19: the resilience curriculum. A guided sequence of runs, each with one
# specific goal that teaches one idea, done in order: the current lesson is the
# only one that can be completed, and it is judged on the run's FINAL state when
# it pays out. Progress is a plain count kept per browser
# (aftermath_curriculum_v1), like the skill tree; the lessons never change
# any number in a run, they only name a goal and notice when it is met.
CURRICULUM_STORAGE_KEY = "aftermath_curriculum_v1"
CURRICULUM = [
    {
        "id": "first_steps",
        "title": "First steps",
        "goal": "Finish a run with resources still in hand.",
        "idea": "A settlement can absorb a bad year if it isn't running on empty.",
        "check": lambda r: r.resources > 0,
    },
    {
        "id": "resilience_first",
        "title": "Resilience first",
        "goal": "Finish with at least 3 resilience and resources still in hand.",
        "idea": "Resilience shrinks every shock that follows it, so it pays back the earlier it is built.",
        "check": lambda r: r.resilience_capacity >= 3 and r.resources > 0,
    },
    {
        "id": "growth_pays",
        "title": "Growth pays",
        "goal": "Finish with at least 2 growth and more resources than you started with.",
        "idea": "Growth is an income that keeps arriving between disasters.",
        "check": lambda r: r.growth_capacity >= 2 and r.resources > r.starting_resources,
    },
    {
        "id": "balance",
        "title": "Balance",
        "goal": "Finish with at least 2 growth, at least 2 resilience and 100+ resources.",
        "idea": "Protection and income together beat either alone.",
        "check": lambda r: r.growth_capacity >= 2 and r.resilience_capacity >= 2 and r.resources >= 100,
    },
    {
        "id": "coastal_test",
        "title": "The coastal test",
        "goal": "Choose the Coastal scenario and finish with resources in hand.",
        "idea": "Different places face different shocks, so the same plan is tested differently.",
        "check": lambda r: r.scenario == "coastal" and r.resources > 0,
    },
]


def load_curriculum_progress():
    raw = localStorage.getItem(CURRICULUM_STORAGE_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, min(len(CURRICULUM), value))


def save_curriculum_progress(value):
    _storage_write(CURRICULUM_STORAGE_KEY, str(value))


def curriculum_current():
    """The lesson the player is on, or None once every lesson is done."""
    if curriculum_progress >= len(CURRICULUM):
        return None
    return CURRICULUM[curriculum_progress]


def note_curriculum_run(finished_run):
    """Called once when a run completes and pays out. If it meets the CURRENT
    lesson's goal, advances the curriculum and returns that lesson; else None."""
    global curriculum_progress
    lesson = curriculum_current()
    if lesson is None or not lesson["check"](finished_run):
        return None
    curriculum_progress += 1
    save_curriculum_progress(curriculum_progress)
    return lesson


def curriculum_message():
    global curriculum_just_completed
    parts = []
    if curriculum_just_completed:
        parts.append(f"Lesson complete: {curriculum_just_completed['title']}. {curriculum_just_completed['idea']}")
        curriculum_just_completed = None
    lesson = curriculum_current()
    if lesson is None:
        parts.append(f"Curriculum complete: all {len(CURRICULUM)} lessons done.")
    else:
        parts.append(
            f"Curriculum, lesson {curriculum_progress + 1} of {len(CURRICULUM)}: {lesson['title']}. Goal: {lesson['goal']}"
        )
    return " ".join(parts)


def load_run_history():
    raw = localStorage.getItem(RUN_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except ValueError:
        return []


def save_run_history(history):
    _storage_write(RUN_HISTORY_STORAGE_KEY, json.dumps(history))


def load_legacy_event_counts():
    """E4: how many times this settlement has weathered each event type,
    additive to (not a replacement for) the pre-existing ever-weathered
    `legacy_events` set above."""
    raw = localStorage.getItem(LEGACY_COUNTS_STORAGE_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): int(value) for key, value in data.items() if isinstance(value, (int, float))}


def save_legacy_event_counts(counts):
    _storage_write(LEGACY_COUNTS_STORAGE_KEY, json.dumps(counts))


def load_run_log_history():
    """E7: the persisted event-by-event breakdown for every completed run
    (a superset of run_history, which only ever stored the final score).
    Starts empty even for a returning player with existing run_history --
    runs completed before this feature shipped simply have no detailed
    breakdown to show, which the review UI handles gracefully."""
    raw = localStorage.getItem(RUN_LOG_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def save_run_log_history(history):
    _storage_write(RUN_LOG_HISTORY_STORAGE_KEY, json.dumps(history))


# Small persistent "settlement meta" dict (E25 settlement name, E30b pinned
# skills, E8/E28 one-time-callout flags). Lives in localStorage next to the
# skill tree, same category and same reasoning (cross-run progress, not
# per-run save-widget state); safe defaults for every field so an older
# browser profile with no such key just gets the empty defaults.
META_STORAGE_KEY = "aftermath_meta_v1"
SETTLEMENT_NAME_MAX = 30
RUN_NOTE_MAX_CHARS = 140
RUN_NOTES_MAX = 500


def _default_meta():
    return {
        "settlement_name": "",
        "pinned_skills": [],
        "seen_negative_tip": False,
        "seen_harsh_callout": False,
        # E-22 / E-21: a short note per completed run (keyed by run number as a string) and the
        # run numbers the player has archived from the Past Runs list.
        "run_notes": {},
        "archived_runs": [],
        # E-25: named allocation presets ([{"name", "resilience", "growth"}]).
        "presets": [],
        # E-13: named player-built schedules ([{"name", "events"}]).
        "custom_schedules": [],
        # E-4: how many friend challenges have been finished, and the best score per code.
        "challenge_runs": 0,
        "challenge_best": {},
    }


PRESET_MAX = 8
PRESET_NAME_MAX = 24
PRESET_UNITS_MAX = 20
CUSTOM_SCHEDULES_MAX = 12
CUSTOM_NAME_MAX = 24
CUSTOM_MIN_EVENTS = 3
CUSTOM_MAX_EVENTS = 7
CHALLENGE_BEST_MAX = 40


def _clean_name(text, limit):
    return " ".join(str(text or "").split())[:limit]


def _units(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = int(value)
    return value if 0 <= value <= PRESET_UNITS_MAX else None


def _sanitize_presets(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name"), PRESET_NAME_MAX)
        resilience, growth = _units(item.get("resilience")), _units(item.get("growth"))
        if not name or resilience is None or growth is None or resilience + growth < 1:
            continue
        if any(p["name"].casefold() == name.casefold() for p in out):
            continue
        out.append({"name": name, "resilience": resilience, "growth": growth})
        if len(out) >= PRESET_MAX:
            break
    return out


def _sanitize_custom_schedules(value):
    out = []
    if not isinstance(value, list):
        return out
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name"), CUSTOM_NAME_MAX)
        events = item.get("events")
        if (
            not name
            or not isinstance(events, list)
            or not CUSTOM_MIN_EVENTS <= len(events) <= CUSTOM_MAX_EVENTS
            or not all(isinstance(e, str) and e in EVENT_LABEL for e in events)
        ):
            continue
        if any(c["name"].casefold() == name.casefold() for c in out):
            continue
        out.append({"name": name, "events": list(events)})
        if len(out) >= CUSTOM_SCHEDULES_MAX:
            break
    return out


def _sanitize_meta(data):
    meta = _default_meta()
    if not isinstance(data, dict):
        return meta
    name = data.get("settlement_name", "")
    if isinstance(name, str):
        meta["settlement_name"] = name.strip()[:SETTLEMENT_NAME_MAX]
    pinned = data.get("pinned_skills", [])
    if isinstance(pinned, list):
        meta["pinned_skills"] = [p for p in pinned if isinstance(p, str)]
    meta["seen_negative_tip"] = bool(data.get("seen_negative_tip", False))
    meta["seen_harsh_callout"] = bool(data.get("seen_harsh_callout", False))
    notes = data.get("run_notes", {})
    if isinstance(notes, dict):
        for key, value in list(notes.items())[:RUN_NOTES_MAX]:
            if isinstance(value, str) and value.strip() and str(key).isdigit():
                meta["run_notes"][str(key)] = value.strip()[:RUN_NOTE_MAX_CHARS]
    archived = data.get("archived_runs", [])
    if isinstance(archived, list):
        meta["archived_runs"] = sorted({a for a in archived if isinstance(a, int) and not isinstance(a, bool) and a > 0})
    meta["presets"] = _sanitize_presets(data.get("presets", []))
    meta["custom_schedules"] = _sanitize_custom_schedules(data.get("custom_schedules", []))
    played = data.get("challenge_runs", 0)
    if isinstance(played, int) and not isinstance(played, bool) and played > 0:
        meta["challenge_runs"] = played
    best = data.get("challenge_best", {})
    if isinstance(best, dict):
        for code, value in list(best.items())[:CHALLENGE_BEST_MAX]:
            if isinstance(code, str) and isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                meta["challenge_best"][code[:90]] = int(value)
    return meta


def load_meta():
    raw = localStorage.getItem(META_STORAGE_KEY)
    if not raw:
        return _default_meta()
    try:
        return _sanitize_meta(json.loads(raw))
    except ValueError:
        return _default_meta()


def save_meta():
    _storage_write(META_STORAGE_KEY, json.dumps(meta))


meta = load_meta()


# E-4: every helper below reads the skill tree through an optional `unlocked`
# argument, so a challenge run (which ignores the player's tree) can pass an
# empty set instead of switching on global state.
def _unlocked_or_tree(unlocked):
    return skill_tree.unlocked if unlocked is None else unlocked


def starting_resources_bonus(unlocked=None):
    return 50 if "community_reserves" in _unlocked_or_tree(unlocked) else 0


def starting_resilience_bonus(unlocked=None):
    return 2 if "reinforced_infrastructure" in _unlocked_or_tree(unlocked) else 0


def early_warning_mitigation_bonus(unlocked=None):
    return 0.10 if "early_warning" in _unlocked_or_tree(unlocked) else 0.0


def growth_income_now(growth_capacity):
    """E20: the growth payoff the player is actually earning right now."""
    return growth_capacity * GROWTH_INCOME_PER_UNIT


def growth_button_label(growth_capacity, units=1):
    """E20: the button shows the real current payoff and what one more
    unit would make it, instead of a static per-unit number. E-15: with a
    bigger step the label names the units and the total cost."""
    count = f" x{units}" if units > 1 else ""
    return (
        f"Invest in Growth{count} ({GROWTH_COST * units}) · +{growth_income_now(growth_capacity)}"
        f" → +{growth_income_now(growth_capacity + units)} resources/event"
    )


def adaptive_growth_bonus(unlocked=None):
    """E2: the fourth skill node -- a starting-growth-capacity bonus,
    mirroring reinforced_infrastructure/community_reserves' starting-stat
    shape but on the growth side instead of resilience/resources."""
    return 1 if "adaptive_growth" in _unlocked_or_tree(unlocked) else 0


def mutual_aid_mitigation_bonus(unlocked=None):
    """E2: the fifth skill node -- flat mitigation like early_warning's,
    but gated behind E3's prereq structure (both foundational skills)."""
    return 0.05 if "mutual_aid_network" in _unlocked_or_tree(unlocked) else 0.0


# E1/E3: per-category damage reduction from the two specialization nodes.
CATEGORY_DAMAGE_BONUS = {
    "civic_preparedness": ("social", 0.35),
    "climate_hardening": ("weather", 0.20),
}


def category_skill_bonus(event_type, unlocked=None):
    """The skill-tree part of the category bonus (civic preparedness, climate hardening)."""
    category = EVENT_CATEGORY.get(event_type)
    tree = _unlocked_or_tree(unlocked)
    return sum(
        amount
        for skill_id, (cat, amount) in CATEGORY_DAMAGE_BONUS.items()
        if cat == category and skill_id in tree
    )


def category_memory_bonus(event_type, memory=None):
    """E29: the societal-memory part of the category bonus."""
    category = EVENT_CATEGORY.get(event_type)
    remembered = societal_memory if memory is None else memory
    return SOCIETAL_MEMORY_BONUS[category] if category in remembered else 0.0


def category_mitigation_bonus(event_type, unlocked=None, memory=None):
    return category_skill_bonus(event_type, unlocked) + category_memory_bonus(event_type, memory)


def worst_damage_category(event_log):
    """E29: the event category that did the most total damage in a run."""
    totals = {}
    for entry in event_log:
        category = EVENT_CATEGORY.get(entry["type"])
        if category:
            totals[category] = totals.get(category, 0.0) + entry["damage"]
    if not totals:
        return None
    return max(sorted(totals), key=lambda c: totals[c])


def record_societal_memory(event_log, score):
    """E29: called once when a run completes and pays out. Returns the newly
    remembered category, or None (not a ruinous run, or already remembered)."""
    if score > VERY_BAD_RUN_SCORE:
        return None
    category = worst_damage_category(event_log)
    if category is None or category in societal_memory:
        return None
    societal_memory.add(category)
    save_societal_memory(societal_memory)
    return category


class RunState:
    def __init__(self, run_number=1, extended=False, scenario=DEFAULT_SCENARIO,
                 normalised=False, draw=None, custom_events=None, custom_name=None, challenge=None):
        """Reads current skill-tree bonuses at creation time — a new run
        starts a little more capable than the last, per unlocked skills.

        `extended` (E18: optional extended-run mode) picks a per-instance
        `schedule` — the same fixed EVENT_SCHEDULE repeated twice for a
        longer, harder-fought run, or the plain schedule otherwise. Every
        schedule-length-dependent method below reads self.schedule rather
        than the module-level EVENT_SCHEDULE directly, so a normal run's
        behavior (and every test pinned to it) is completely unchanged —
        only a run explicitly started as `extended` ever sees the longer
        list."""
        self.run_number = run_number
        self.extended = extended
        # E17a: which scenario's schedule this run follows (unknown names
        # fall back to the classic mix).
        self.scenario = scenario if isinstance(scenario, str) and scenario in SCENARIOS else DEFAULT_SCENARIO
        base_schedule = SCENARIOS[self.scenario]["schedule"]
        self.schedule = base_schedule * 2 if extended else base_schedule
        # E-13: a player-built schedule replaces the scenario's (never extended).
        self.custom_events = None
        self.custom_name = None
        if custom_events and all(e in EVENT_LABEL for e in custom_events):
            self.custom_events = list(custom_events)
            self.custom_name = custom_name if isinstance(custom_name, str) and custom_name else None
            self.schedule = list(custom_events)
            self.extended = False
        # E-4: a challenge run (a friend's run code) ignores the player's own tree: no starting
        # bonuses, no skill or memory mitigation, severity from the code's draw at the
        # un-widened band. `challenge` keeps the code and the sender's result for comparison.
        self.normalised = bool(normalised)
        self.draw = int(draw) if draw is not None else run_number
        self.challenge = challenge if self.normalised and isinstance(challenge, dict) else None
        self.event_index = 0
        self.resources = STARTING_RESOURCES + starting_resources_bonus(self._unlocked())
        self.resilience_capacity = starting_resilience_bonus(self._unlocked())
        self.growth_capacity = adaptive_growth_bonus(self._unlocked())
        self.damage_taken = 0.0
        self.event_log = []
        # Achievements ("profitable_run") need to compare a run's *final*
        # resources against what it actually started with -- which varies
        # run to run once skill-tree bonuses affect starting resources, so
        # this is captured once here rather than re-deriving it later from
        # STARTING_RESOURCES + starting_resources_bonus() (the latter would
        # silently drift if more skills unlock mid-run... they can't, but
        # capturing it explicitly avoids relying on that being true).
        self.starting_resources = self.resources
        # GE-18: one entry per allocation click this between-event phase, as
        # (kind, units). Not part of get_state(): after a load, or once an
        # event resolves, there is nothing to undo.
        self.allocation_history = []
        # E-18: how the most recent event's damage was worked out. In memory
        # only (never saved): after a load there is no breakdown to show.
        self.last_breakdown = None

    def _unlocked(self):
        return frozenset() if self.normalised else skill_tree.unlocked

    def _memory(self):
        return frozenset() if self.normalised else societal_memory

    def category_bonus(self, event_type):
        return category_mitigation_bonus(event_type, self._unlocked(), self._memory())

    def severity_at(self, index):
        """The severity multiplier for event `index` of this run: the player's own pattern
        (widened by their tree and career), or, in a challenge run, the code's fixed draw at the
        plain band so both players face the same numbers."""
        if self.normalised:
            return event_severity(self.draw, index, 0, 0)
        return event_severity(self.run_number, index, skill_tree_strength())

    def is_complete(self):
        return self.event_index >= len(self.schedule)

    def next_event_type(self):
        if self.is_complete():
            return None
        return self.schedule[self.event_index]

    def invest_resilience(self, record=True):
        if self.resources < RESILIENCE_COST:
            return False
        self.resources -= RESILIENCE_COST
        self.resilience_capacity += 1
        if record:
            self._record_allocation("resilience", 1)
        _note_achievement_progress(ever_invested_resilience=True)
        if self.mitigation_fraction() >= MAX_MITIGATION:
            _note_achievement_progress(ever_maxed_mitigation=True)
        return True

    def invest_growth(self, record=True):
        if self.resources < GROWTH_COST:
            return False
        self.resources -= GROWTH_COST
        self.growth_capacity += 1
        if record:
            self._record_allocation("growth", 1)
        _note_achievement_progress(ever_invested_growth=True)
        return True

    # GE-18: undo of allocation clicks before Resolve.
    def _record_allocation(self, kind, units):
        self.allocation_history.append((kind, units))

    def undo_count(self):
        return len(self.allocation_history)

    def undo_last_allocation(self):
        """Gives back the last allocation click's units and resources. Only
        possible before the next Resolve (resolving clears the history)."""
        if not self.allocation_history or self.is_complete():
            return False
        kind, units = self.allocation_history.pop()
        if kind == "resilience":
            self.resilience_capacity -= units
            self.resources += RESILIENCE_COST * units
        elif kind == "preset":  # E-25: one click bought resilience and growth together
            self.resilience_capacity -= units[0]
            self.resources += RESILIENCE_COST * units[0]
            self.growth_capacity -= units[1]
            self.resources += GROWTH_COST * units[1]
        else:
            self.growth_capacity -= units
            self.resources += GROWTH_COST * units
        return True

    # E-15: x1 / x5 / Max steps.
    def _raw_mitigation(self):
        return (
            self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
            + early_warning_mitigation_bonus(self._unlocked())
            + mutual_aid_mitigation_bonus(self._unlocked())
        )

    def resilience_units_to_cap(self):
        """How many more resilience units fit before general mitigation
        reaches MAX_MITIGATION (more would be wasted)."""
        gap = MAX_MITIGATION - self._raw_mitigation()
        if gap <= 1e-9:
            return 0
        return int(math.ceil(gap / RESILIENCE_MITIGATION_PER_UNIT - 1e-9))

    def step_units(self, kind, step):
        """Units one click buys at this step size: 1, 5 or "max". x1 keeps
        the original rule (one unit whenever it is affordable); x5 and Max
        stop at the resource limit and, for resilience, at the 85% cap."""
        cost = RESILIENCE_COST if kind == "resilience" else GROWTH_COST
        affordable = int(self.resources // cost)
        if step == 1:
            return 1 if affordable >= 1 else 0
        if kind == "resilience":
            affordable = min(affordable, self.resilience_units_to_cap())
        if step == "max":
            return affordable
        return min(int(step), affordable)

    def invest_steps(self, kind, step):
        """Buys step_units() units as ONE undoable click. Returns the
        number bought (0 when nothing was affordable)."""
        if self.is_complete():
            return 0
        units = self.step_units(kind, step)
        bought = 0
        for _ in range(units):
            ok = self.invest_resilience(record=False) if kind == "resilience" else self.invest_growth(record=False)
            if not ok:
                break
            bought += 1
        if bought:
            self._record_allocation(kind, bought)
        return bought

    def invest_preset(self, resilience, growth):
        """E-25: buys up to `resilience` then `growth` units as ONE undoable click, limited by the
        resources in hand (and, for resilience, by the 85% cap, like x5 and Max). Returns the units
        actually bought as (resilience, growth)."""
        if self.is_complete():
            return 0, 0
        bought_r = bought_g = 0
        for _ in range(min(resilience, self.resilience_units_to_cap())):
            if not self.invest_resilience(record=False):
                break
            bought_r += 1
        for _ in range(growth):
            if not self.invest_growth(record=False):
                break
            bought_g += 1
        if bought_r or bought_g:
            self._record_allocation("preset", (bought_r, bought_g))
        return bought_r, bought_g

    def mitigation_fraction(self):
        from_resilience = self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
        return min(
            MAX_MITIGATION,
            from_resilience + early_warning_mitigation_bonus(self._unlocked()) + mutual_aid_mitigation_bonus(self._unlocked()),
        )

    def mitigation_for(self, event_type):
        """Total damage reduction for one event: the general mitigation
        plus any category-specific specialization bonus, still capped at
        MAX_MITIGATION so nothing ever reaches full immunity."""
        return min(MAX_MITIGATION, self.mitigation_fraction() + self.category_bonus(event_type))

    def damage_breakdown(self, event_type, severity):
        """E-18: base damage, the severity change, each mitigation source (in
        damage points) and the final damage, in the order the rules apply
        them. general = resilience + early warning + mutual aid is capped at
        MAX_MITIGATION, then the category bonus is added and the total capped
        again; `cap_added_back` is whatever those caps gave back."""
        base = EVENT_BASE_DAMAGE[event_type]
        unmitigated = base * severity
        sources = [
            ("Resilience investment", self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT),
            ("Early Warning Systems", early_warning_mitigation_bonus(self._unlocked())),
            ("Mutual Aid Network", mutual_aid_mitigation_bonus(self._unlocked())),
            ("Category skill", category_skill_bonus(event_type, self._unlocked())),
            ("Societal memory", category_memory_bonus(event_type, self._memory())),
        ]
        general_raw = sources[0][1] + sources[1][1] + sources[2][1]
        general = min(MAX_MITIGATION, general_raw)
        total = min(MAX_MITIGATION, general + sources[3][1] + sources[4][1])
        raw_total = sum(amount for _, amount in sources)
        return {
            "type": event_type,
            "base": base,
            "severity": severity,
            "unmitigated": unmitigated,
            "sources": [
                {"label": label, "fraction": amount, "damage": unmitigated * amount}
                for label, amount in sources
                if amount > 0
            ],
            "cap_added_back": unmitigated * (raw_total - total),
            "mitigation": total,
            "final": unmitigated * (1 - total),
        }

    def resolve_next_event(self):
        """Applies growth income, then resolves the next scheduled event's
        damage (reduced by resilience mitigation). No-op once the run is
        complete."""
        if self.is_complete():
            return False

        self.resources += self.growth_capacity * GROWTH_INCOME_PER_UNIT

        event_type = self.schedule[self.event_index]
        severity = self.severity_at(self.event_index)
        damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - self.mitigation_for(event_type))
        self.last_breakdown = self.damage_breakdown(event_type, severity)  # E-18
        self.resources = max(0.0, self.resources - damage)
        self.damage_taken += damage
        self.event_log.append({"type": event_type, "damage": damage, "severity": severity})
        self.event_index += 1
        self.allocation_history = []  # GE-18: nothing to undo after Resolve
        if entry_is_flawless(self.event_log[-1]):
            _note_achievement_progress(ever_flawless_defense=True)  # GE-15

        _note_achievement_progress(ever_faced_event=True)
        if severity_label(severity) == "severe" and self.resources > 0:
            _note_achievement_progress(ever_survived_severe_event=True)

        if self.is_complete() and self.normalised:
            _note_challenge_result(self)  # E-4: a friend's challenge earns nothing for the tree
        elif self.is_complete():
            global highest_awarded_run
            if self.run_number > highest_awarded_run:
                skill_tree.add_knowledge(self.knowledge_points_earned())
                skill_tree.save()
                run_history.append(self.run_score())
                save_run_history(run_history)
                global memory_just_formed, curriculum_just_completed
                memory_just_formed = record_societal_memory(self.event_log, self.run_score())  # E29
                curriculum_just_completed = None if self.custom_events else note_curriculum_run(self)  # E19
                legacy_events.update(entry["type"] for entry in self.event_log)
                save_legacy_events(legacy_events)
                # E4: build out the legacy system beyond its original
                # single-flavor-text-line shape -- a per-event-type
                # *count* of how many times this settlement has weathered
                # each kind of event, alongside the pre-existing
                # ever-weathered set above (which legacy_message() still
                # uses unchanged).
                for entry in self.event_log:
                    legacy_event_counts[entry["type"]] = legacy_event_counts.get(entry["type"], 0) + 1
                save_legacy_event_counts(legacy_event_counts)
                # E7: persist this run's full event-by-event breakdown
                # (not just its final score, which run_history already
                # tracks) so players can review a specific past run later.
                run_log_history.append(
                    {
                        "run_number": self.run_number,
                        "score": self.run_score(),
                        "resilience_capacity": self.resilience_capacity,
                        "growth_capacity": self.growth_capacity,
                        "damage_taken": self.damage_taken,
                        "knowledge_earned": self.knowledge_points_earned(),
                        # E-1: the skill-tree strength this run was played at
                        # (older logs lack it and are left out of the band stat).
                        "skill_strength": skill_tree_strength(),
                        "event_log": copy.deepcopy(self.event_log),
                        # E-13: runs on a player-built schedule are tagged (older logs lack the field).
                        **({"custom_schedule": self.custom_name or "Unnamed"} if self.custom_events else {}),
                    }
                )
                save_run_log_history(run_log_history)
                highest_awarded_run = self.run_number
                save_highest_awarded_run(highest_awarded_run)
                _season_run_finished(self.resources)
                if not self.custom_events:  # E-13: a hand-built schedule never competes on the board
                    _report_hardest_schedule(self)  # E23

                # Playstyle achievements -- only recorded the first time a
                # given run_number genuinely completes (same guard as the
                # knowledge/history/legacy payout above), so reloading a
                # stale pre-completion save and re-resolving it can't
                # re-trigger these either.
                if self.resources > self.starting_resources:
                    _note_achievement_progress(ever_profitable_run=True)
                if self.growth_capacity >= 3 and self.growth_capacity > self.resilience_capacity:
                    _note_achievement_progress(ever_growth_heavy_run=True)
                if self.resilience_capacity >= 3 and self.resilience_capacity > self.growth_capacity:
                    _note_achievement_progress(ever_resilience_heavy_run=True)
                if self.growth_capacity >= 2 and self.growth_capacity == self.resilience_capacity:
                    _note_achievement_progress(ever_balanced_run=True)
                # E15: a narrow deep-investment run (5+ in one track, none
                # in the other) and a broad run (3+ in both) are both
                # rewarded; a third achievement needs both.
                if max(self.growth_capacity, self.resilience_capacity) >= 5 and min(
                    self.growth_capacity, self.resilience_capacity
                ) == 0:
                    _note_achievement_progress(ever_deep_specialist_run=True)
                if self.growth_capacity >= 3 and self.resilience_capacity >= 3:
                    _note_achievement_progress(ever_broad_generalist_run=True)

        return True

    def run_score(self):
        """How well the settlement weathered the run — just the resources
        it has left. Reflects both good mitigation (less damage) and good
        growth (more income to absorb it)."""
        return self.resources

    def knowledge_points_earned(self):
        """Currency for the skill tree. Floored at 1 — per the hope angle,
        even a rough run always contributes some permanent capability,
        never zero. GE-15: each Flawless Defense adds a bonus point."""
        return self.knowledge_breakdown()["total"]

    def knowledge_breakdown(self):
        """E-23: where the run's knowledge points come from."""
        raw = round(self.run_score() / 20)
        base = max(1, raw)
        factor = self.custom_knowledge_factor()
        if factor < 1.0:
            base = max(1, round(base * factor))
        flawless = flawless_count(self.event_log)
        bonus = flawless * FLAWLESS_BONUS_KNOWLEDGE
        return {
            "resources": self.run_score(),
            "raw": raw,
            "base": base,
            "floor_applied": raw < 1,
            "flawless": flawless,
            "flawless_bonus": bonus,
            "total": base + bonus,
            "schedule_factor": factor,
        }

    def custom_knowledge_factor(self):
        """E-13: a hand-built schedule earns knowledge in proportion to how much damage it throws
        compared with the Classic mix (at most the full amount), so a short, gentle schedule
        cannot be farmed for knowledge. Every built-in scenario and the extended run are
        untouched (factor 1.0)."""
        if not self.custom_events:
            return 1.0
        total = sum(EVENT_BASE_DAMAGE[e] for e in self.custom_events)
        reference = sum(EVENT_BASE_DAMAGE[e] for e in EVENT_SCHEDULE)
        return min(1.0, total / reference)


SKILL_MOVE_FEE = 1  # AN-13: knowledge a move of one point costs (the lifetime total never changes)


class SkillTreeState:
    """Persistent, separate from RunState — survives across runs and, via
    localStorage, across visits (same browser)."""

    def __init__(self):
        self.knowledge_points = 0
        self.unlocked = set()
        # Lifetime total ever earned -- unlike knowledge_points (a spendable
        # balance that drops on unlock), this only ever grows, so it's the
        # correct signal for a "earn N knowledge points over your
        # settlement's lifetime" achievement (knowledge_25/knowledge_100).
        self.lifetime_knowledge = 0

    def can_unlock(self, skill_id):
        """E3: branching/prerequisite structure — a skill is unlockable
        only once every id in its own "prereqs" list is itself already
        unlocked (empty for the three original skills, so they're
        unaffected)."""
        skill = SKILLS[skill_id]
        if skill_id in self.unlocked or self.knowledge_points < skill["cost"]:
            return False
        return all(prereq in self.unlocked for prereq in skill.get("prereqs", []))

    def missing_prereqs(self, skill_id):
        """The subset of skill_id's prereqs not yet unlocked, in catalog
        order — used to tell the player *why* a skill is locked (E3)."""
        return [prereq for prereq in SKILLS[skill_id].get("prereqs", []) if prereq not in self.unlocked]

    def unlock(self, skill_id):
        if not self.can_unlock(skill_id):
            return False
        self.knowledge_points -= SKILLS[skill_id]["cost"]
        self.unlocked.add(skill_id)
        self.save()
        return True

    def move_check(self, from_id, to_id):
        """AN-13: moving ONE point from an owned skill to another costs SKILL_MOVE_FEE knowledge (never a
        restart). Returns (ok, reason in plain words). Rules: both must be real skills; the first owned and
        the second not; nothing else owned may need the first one; the second's prerequisites must still be
        met without the first; the refund plus the balance must cover the second skill and the fee."""
        if from_id not in SKILLS or to_id not in SKILLS or from_id == to_id:
            return False, "Pick one skill you own and a different skill to move to."
        if from_id not in self.unlocked:
            return False, f"{SKILLS[from_id]['label']} is not one of your skills."
        if to_id in self.unlocked:
            return False, f"{SKILLS[to_id]['label']} is already yours."
        dependants = [SKILLS[s]["label"] for s in self.unlocked if s != from_id and from_id in SKILLS[s].get("prereqs", [])]
        if dependants:
            return False, f"{SKILLS[from_id]['label']} is needed by {', '.join(sorted(dependants))}, so it cannot be moved."
        missing = [SKILLS[p]["label"] for p in SKILLS[to_id].get("prereqs", []) if p not in self.unlocked or p == from_id]
        if missing:
            return False, f"{SKILLS[to_id]['label']} needs {', '.join(missing)} first."
        left = self.knowledge_points + SKILLS[from_id]["cost"] - SKILLS[to_id]["cost"] - SKILL_MOVE_FEE
        if left < 0:
            return False, f"You would be {-left} knowledge short (the move costs {SKILL_MOVE_FEE} on top of the difference)."
        return True, ""

    def move(self, from_id, to_id):
        ok, _reason = self.move_check(from_id, to_id)
        if not ok:
            return False
        self.knowledge_points += SKILLS[from_id]["cost"] - SKILLS[to_id]["cost"] - SKILL_MOVE_FEE
        self.unlocked.discard(from_id)
        self.unlocked.add(to_id)
        self.save()
        return True

    def add_knowledge(self, amount):
        self.knowledge_points += amount
        self.lifetime_knowledge += amount

    def to_dict(self):
        return {
            "knowledge_points": self.knowledge_points,
            "unlocked": sorted(self.unlocked),
            "lifetime_knowledge": self.lifetime_knowledge,
        }

    def save(self):
        _storage_write(SKILL_TREE_STORAGE_KEY, json.dumps(self.to_dict()))

    @classmethod
    def load(cls):
        instance = cls()
        raw = localStorage.getItem(SKILL_TREE_STORAGE_KEY)
        if not raw:
            return instance
        try:
            data = json.loads(raw)
        except ValueError:
            return instance
        instance.knowledge_points = data.get("knowledge_points", 0)
        instance.unlocked = set(data.get("unlocked", []))
        # Defensive fallback for a save made before this field existed
        # (ACHIEVEMENTS-SYSTEM-DESIGN.md §4's pattern): default to whatever
        # the current spendable balance is rather than 0, so an existing
        # player's lifetime total isn't understated the moment this field
        # ships -- an underestimate (missing already-spent knowledge) is
        # far less surprising than a stale save silently reporting fewer
        # lifetime points than the player can literally see they're holding.
        instance.lifetime_knowledge = data.get("lifetime_knowledge", instance.knowledge_points)
        return instance


skill_tree = SkillTreeState.load()
run_history = load_run_history()
legacy_events = load_legacy_events()
societal_memory = load_societal_memory()  # E29
memory_just_formed = None  # E29: the category remembered by the run that just completed, for one callout
curriculum_progress = load_curriculum_progress()  # E19
curriculum_just_completed = None  # E19: the lesson the run that just completed finished, for one callout
legacy_event_counts = load_legacy_event_counts()
run_log_history = load_run_log_history()
highest_awarded_run = load_highest_awarded_run()
run = RunState()


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL/Canopy/Grid's
# reference integrations. Every achievement's earned status is a pure
# function of state that already exists elsewhere in this module, recomputed
# fresh every call — never a separately hand-maintained "earned" flag.
#
# Several achievements here genuinely can't be derived from run_history/
# skill_tree/legacy_events alone: things like "ever invested in Resilience"
# or "ever finished a run in profit" are facts about a *specific run's*
# transient RunState, which resets every new run (§4's five-step pattern
# from the design doc — a persistent fact needs its own persistent tracked
# state, or it would flicker unearned the instant a new run starts). Those
# live in `achievement_progress`, a small persistent dict alongside the
# skill tree/run history/legacy events already in localStorage, mutated
# only where the real event happens (inside RunState's own methods, since
# that's where each of these facts actually becomes true) and otherwise
# read-only from every achievement checker below.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"
ACHIEVEMENT_PROGRESS_STORAGE_KEY = "aftermath_achievement_progress_v1"


def _read_achievements_json():
    """Same loading contract as SOL/Canopy/Grid's `_read_achievements_json()`:
    the boot script fetches achievements.json and hands it to Python as a
    window global before this file runs; the pytest harness's fake `js`
    module has no such attribute, so this falls through to reading the file
    straight off disk, keeping the module importable outside a real
    browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Aftermath's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

RUN_COMPLETE_TARGETS = {"run_complete_1": 1, "run_complete_5": 5, "run_complete_10": 10}
KNOWLEDGE_TARGETS = {"knowledge_25": 25, "knowledge_100": 100}
SKILL_ACHIEVEMENT_IDS = {
    "reinforced_infrastructure": "unlock_reinforced_infrastructure",
    "community_reserves": "unlock_community_reserves",
    "early_warning": "unlock_early_warning",
}


def _default_achievement_progress():
    return {
        "ever_faced_event": False,
        "ever_invested_resilience": False,
        "ever_invested_growth": False,
        "ever_maxed_mitigation": False,
        "ever_survived_severe_event": False,
        "ever_profitable_run": False,
        "ever_growth_heavy_run": False,
        "ever_resilience_heavy_run": False,
        "ever_balanced_run": False,
        # E15: build-diversity family.
        "ever_deep_specialist_run": False,
        "ever_broad_generalist_run": False,
        # GE-15: a Flawless Defense (event damage held to 15% of base).
        "ever_flawless_defense": False,
    }


def load_achievement_progress():
    progress = _default_achievement_progress()
    raw = localStorage.getItem(ACHIEVEMENT_PROGRESS_STORAGE_KEY)
    if not raw:
        return progress
    try:
        data = json.loads(raw)
    except ValueError:
        return progress
    if isinstance(data, dict):
        for key in progress:
            if key in data:
                progress[key] = bool(data[key])
    return progress


def save_achievement_progress():
    _storage_write(ACHIEVEMENT_PROGRESS_STORAGE_KEY, json.dumps(achievement_progress))


achievement_progress = load_achievement_progress()


def _note_achievement_progress(**updates):
    """Sets one or more achievement_progress flags to True (only ever True
    — these are one-way "has this ever happened" facts, never unset) and
    persists if anything actually changed."""
    changed = False
    for key, value in updates.items():
        if value and not achievement_progress.get(key):
            achievement_progress[key] = True
            changed = True
    if changed:
        save_achievement_progress()


def _full_skill_tree_earned():
    return all(skill_id in skill_tree.unlocked for skill_id in SKILLS)


ACHIEVEMENT_CHECKS = {
    "first_event_faced": lambda: achievement_progress["ever_faced_event"],
    "first_resilience_investment": lambda: achievement_progress["ever_invested_resilience"],
    "first_growth_investment": lambda: achievement_progress["ever_invested_growth"],
    "run_complete_1": lambda: len(run_history) >= RUN_COMPLETE_TARGETS["run_complete_1"],
    "run_complete_5": lambda: len(run_history) >= RUN_COMPLETE_TARGETS["run_complete_5"],
    "run_complete_10": lambda: len(run_history) >= RUN_COMPLETE_TARGETS["run_complete_10"],
    "unlock_reinforced_infrastructure": lambda: "reinforced_infrastructure" in skill_tree.unlocked,
    "unlock_community_reserves": lambda: "community_reserves" in skill_tree.unlocked,
    "unlock_early_warning": lambda: "early_warning" in skill_tree.unlocked,
    "full_skill_tree": _full_skill_tree_earned,
    "knowledge_25": lambda: skill_tree.lifetime_knowledge >= KNOWLEDGE_TARGETS["knowledge_25"],
    "knowledge_100": lambda: skill_tree.lifetime_knowledge >= KNOWLEDGE_TARGETS["knowledge_100"],
    "iron_defenses": lambda: achievement_progress["ever_maxed_mitigation"],
    "severe_survivor": lambda: achievement_progress["ever_survived_severe_event"],
    "profitable_run": lambda: achievement_progress["ever_profitable_run"],
    "growth_focused": lambda: achievement_progress["ever_growth_heavy_run"],
    "resilience_focused": lambda: achievement_progress["ever_resilience_heavy_run"],
    "balanced_strategy": lambda: achievement_progress["ever_balanced_run"],
    "deep_specialist": lambda: achievement_progress["ever_deep_specialist_run"],
    "broad_generalist": lambda: achievement_progress["ever_broad_generalist_run"],
    "both_paths": lambda: achievement_progress["ever_deep_specialist_run"]
    and achievement_progress["ever_broad_generalist_run"],
    "come_back_stronger": lambda: len(run_history) >= 2 and run_history[-1] > run_history[0],
    # GE-15 / E-12: collector and mastery achievements.
    "flawless_defense": lambda: achievement_progress["ever_flawless_defense"],
    "codex_complete": lambda: all(t in legacy_events for t in CODEX_CORE_TYPES),
    "codex_full_record": lambda: all(t in legacy_events for t in EVENT_LABEL),
    "heat_health_faced": lambda: "heat_mortality" in legacy_events,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone.
ACHIEVEMENT_PROGRESS = {
    "run_complete_5": lambda: (min(len(run_history), 5), 5),
    "run_complete_10": lambda: (min(len(run_history), 10), 10),
    "full_skill_tree": lambda: (len(skill_tree.unlocked & set(SKILLS)), len(SKILLS)),
    "knowledge_25": lambda: (min(skill_tree.lifetime_knowledge, 25), 25),
    "knowledge_100": lambda: (min(skill_tree.lifetime_knowledge, 100), 100),
    "codex_complete": lambda: (sum(1 for t in CODEX_CORE_TYPES if t in legacy_events), len(CODEX_CORE_TYPES)),
    "codex_full_record": lambda: (sum(1 for t in EVENT_LABEL if t in legacy_events), len(EVENT_LABEL)),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False


# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as SOL's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest resilience/growth, resolve an event, unlock a skill, start a
    new run) — never from render() itself, since load_state() also calls
    render() and a loaded save with several achievements already earned
    must not flood the player with toasts for all of them at once (see
    _seed_achievement_toast_baseline)."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub Pages
    # subpath fix). Rebuilt each open alongside the cards since the panel
    # is cleared first. Note: the hub-side script.js registration that
    # makes Aftermath's save data actually show up on that dashboard is a
    # root-file change, out of scope for this games/aftermath/-only
    # dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# N-2: seasonal event badges (shared/seasonal-events.js grants them; this list is the copy that rides the save).
EVENT_BADGE_MAX = 40
event_badges = []


def _clean_event_badges(raw):
    """Keep only well-formed hub badge entries ({id, label, earned_at}); drop duplicates and junk."""
    out = []
    seen = set()
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        badge_id, label, earned = item.get("id"), item.get("label"), item.get("earned_at", "")
        if not (isinstance(badge_id, str) and 1 <= len(badge_id) <= 64 and badge_id not in seen):
            continue
        if not all(c.isascii() and (c.islower() or c.isdigit() or c == "-") for c in badge_id):
            continue
        if not (isinstance(label, str) and 1 <= len(label.strip()) <= 80):
            continue
        if not (isinstance(earned, str) and len(earned) <= 32):
            earned = ""
        seen.add(badge_id)
        out.append({"id": badge_id, "label": label.strip(), "earned_at": earned})
        if len(out) >= EVENT_BADGE_MAX:
            break
    return out


def set_event_badges(badges_json):
    """Called by the page (shared/seasonal-events.js onGrant) with the whole badge list as JSON text."""
    global event_badges
    try:
        event_badges = _clean_event_badges(json.loads(badges_json))
    except (TypeError, ValueError):
        return False
    return True


def _season_hook(name, argument):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, name, None)
    if hook is not None:
        hook(argument)


def _season_run_finished(resources_left):
    """N-2 Halloween task ("Night of Storms"): the page counts a finished run with resources left."""
    _season_hook("aftermathRunFinished", resources_left)


def societal_memory_message():
    """E29: what the settlement remembers, plus a one-time note the round a
    memory forms."""
    global memory_just_formed
    parts = []
    if memory_just_formed:
        bonus = round(SOCIETAL_MEMORY_BONUS[memory_just_formed] * 100)
        parts.append(
            f"That run left a mark: your settlement will remember {SOCIETAL_MEMORY_LABEL[memory_just_formed]} "
            f"and take {bonus}% less damage from that kind of shock from now on."
        )
        memory_just_formed = None
    if societal_memory:
        remembered = ", ".join(sorted(societal_memory))
        parts.append(f"Societal memory: {remembered} shocks (permanent protection earned the hard way).")
    return " ".join(parts)


def legacy_message():
    if not legacy_events:
        return "No history yet — this is the settlement's first trial."
    labels = sorted(EVENT_LABEL[event_type] for event_type in legacy_events)
    return (
        f"This settlement has weathered {', '.join(labels)} before — every run's "
        f"damage becomes part of what the next one is built to withstand."
    )


def progress_comparison():
    """The hope-angle payoff: run 1 vs. the most recent run, same event
    schedule. None until at least two runs have been completed."""
    if len(run_history) < 2:
        return None
    return run_history[0], run_history[-1]


def progress_message(comparison):
    if comparison is None:
        return "Play more runs to see how far you've come."
    first, latest = comparison
    if latest > first:
        return (
            f"Look how far you've come — your first run scored {first:.0f}, "
            f"your most recent scored {latest:.0f}. Same events, handled better."
        )
    if latest < first:
        return f"Your most recent run ({latest:.0f}) scored lower than your first ({first:.0f})."
    return f"Your run performance has held steady at {latest:.0f}."


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Adaptation — building resilience to climate impacts already "
        "locked in — is treated by climate science and policy as its own "
        "necessary response, not a fallback for failed mitigation. Real "
        "communities that invested early in resilient infrastructure have "
        "documented, measurable payoffs. Aftermath's resource-allocation "
        "choices and its \"how far you've come\" comparison are modeled "
        "on that same idea."
    ),
    "mechanic_tie_in": (
        "The skill tree's resilience/growth split mirrors a real, "
        "documented tradeoff facing infrastructure investment: pay up "
        "front for resilience, or grow capacity and risk being caught "
        "underprepared."
    ),
    "sources": [
        {
            "label": "IPCC AR6 Working Group II — Climate Change 2022: Impacts, Adaptation and Vulnerability",
            "url": "https://www.ipcc.ch/report/ar6/wg2/",
            "note": "The authoritative global reference on adaptation as a distinct climate response, backing Aftermath's core framing.",
        },
        {
            "label": "World Resources Institute — Accelerating Climate-resilient Infrastructure Investment in China",
            "url": "https://www.wri.org/research/accelerating-climate-resilient-infrastructure-investment-china",
            "note": "A real resilience-infrastructure investment case study, grounding Aftermath's resource-allocation mechanic.",
        },
        {
            "label": "World Resources Institute — Driving System Shifts for Climate Resilience (Bhutan, Ethiopia, Costa Rica)",
            "url": "https://www.wri.org/research/driving-system-shifts-climate-resilience-case-studies-transformative-adaptation-bhutan",
            "note": "Real communities' documented adaptation journeys — strong backing for the \"look how far you've come\" hope angle.",
        },
        {
            "label": "EU Mission on Adaptation to Climate Change — Success Stories",
            "url": "https://mission-adaptation-portal.ec.europa.eu/stories-0_en",
            "note": "A running collection of real municipal adaptation wins — concrete \"this actually worked\" examples.",
        },
    ],
}
info_page_open = False


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


# ===========================================================================
# E4: legacy-system expansion (beyond the original single flavor-text line
# above). legacy_message() and the ever-weathered `legacy_events` set are
# untouched -- this is an additive, more detailed view built from the new
# per-event-type `legacy_event_counts`.
# ===========================================================================
def legacy_history_summary():
    """Every event type this settlement has ever weathered, with how many
    times, sorted by label for a stable display order. Empty entries
    (count 0, which shouldn't occur but would if a saved dict somehow had
    a zero) are skipped."""
    return [
        {
            "type": event_type,
            "label": EVENT_LABEL[event_type],
            "icon": EVENT_ICON[event_type],
            "count": count,
        }
        for event_type, count in sorted(legacy_event_counts.items(), key=lambda pair: EVENT_LABEL[pair[0]])
        if count > 0
    ]


# ===========================================================================
# V-CD-6: legacy weathering scars -- a genuinely visual marker on the
# settlement itself, referencing prior-run history, addressing the
# completion-audit finding that E4 above only ever produced a text chip
# row (legacy_history_summary()), not any visual marker on the settlement
# as the original Pass-2 idea described. One scar per event *category*
# (not one per exact event type -- six more rooftop-style dots stacked on
# top of the eight skill/toughest badges the settlement already carries
# would be exactly the crowding problem the UI-decluttering pass above
# was written to avoid), escalating through three tiers as that
# category's aggregated legacy_event_counts total climbs. Purely derived
# from already-persisted legacy_event_counts -- no new storage key.
# ===========================================================================
LEGACY_SCAR_CATEGORIES = ("weather", "non-weather", "social", "health")
LEGACY_SCAR_TIER_THRESHOLDS = (1, 3, 6)  # cumulative count needed for tier 1 / 2 / 3


def legacy_category_totals():
    """Aggregate legacy_event_counts (per exact event type, cross-run) up
    to the three event categories, so the settlement's ground shows one
    scar per category rather than one per exact event type. Always
    returns all three categories, 0 where nothing of that category has
    ever been weathered yet."""
    totals = {category: 0 for category in LEGACY_SCAR_CATEGORIES}
    for event_type, count in legacy_event_counts.items():
        category = EVENT_CATEGORY.get(event_type)
        if category in totals:
            totals[category] += count
    return totals


def legacy_scar_tier(count):
    """0 (no scar yet) through 3 (heaviest), from how many times this
    settlement has weathered that category across every run ever
    played."""
    tier = 0
    for threshold in LEGACY_SCAR_TIER_THRESHOLDS:
        if count >= threshold:
            tier += 1
    return tier


def legacy_scar_tiers():
    return {category: legacy_scar_tier(total) for category, total in legacy_category_totals().items()}


# ===========================================================================
# E7: reviewing a specific past run's full event-by-event breakdown, from
# the new run_log_history persisted alongside (not instead of) the
# existing run_history score-only list.
# ===========================================================================
past_runs_open = False


# E27: the resilience mentor. An OPTIONAL guided mode (off by default, saved per
# browser, distinct from the one-time tutorial): one inline suggestion, right
# where the decision is made, that reads the live run and says what it would
# do and why. Advice only: it never acts for the player and never changes any
# number. Rules are checked in order and the first that applies wins.
MENTOR_STORAGE_KEY = "aftermath_mentor_v1"
mentor_enabled = False


def load_mentor_enabled():
    return localStorage.getItem(MENTOR_STORAGE_KEY) == "1"


def mentor_suggestion(run_state):
    """The single most useful piece of advice for this moment, as one sentence."""
    if run_state.is_complete():
        return (
            "The run is over. Spend the knowledge you earned in the skill tree: even a rough run "
            "always leaves the next one a little stronger."
        )
    event_type = run_state.next_event_type()
    label = EVENT_LABEL[event_type]
    expected, _severity = expected_next_event_damage(run_state)
    resilience_cost = RESILIENCE_COST
    if run_state.event_index == 0 and run_state.resilience_capacity == 0 and run_state.growth_capacity == 0:
        return (
            f"Start by choosing a balance. Resilience ({resilience_cost} resources) cuts the damage of every shock; "
            f"growth ({GROWTH_COST} resources) earns {GROWTH_INCOME_PER_UNIT} more each round. "
            f"A {label} is coming first."
        )
    if expected >= run_state.resources:
        if run_state.resources >= resilience_cost:
            return (
                f"Careful: the coming {label} would take about {expected:.0f} and you have {run_state.resources:.0f}. "
                f"Put resources into resilience now to shrink the hit."
            )
        return (
            f"The coming {label} could take about {expected:.0f} of your {run_state.resources:.0f}. "
            f"You can't afford resilience right now, so brace: the run still teaches something."
        )
    if run_state.resilience_capacity == 0:
        return (
            f"You have no resilience yet, so the {label} lands at full force (about {expected:.0f}). "
            f"One resilience purchase would already soften every shock after it."
        )
    if run_state.growth_capacity == 0 and run_state.event_index >= 2 and run_state.resources >= GROWTH_COST:
        return (
            "You have no growth: every event drains a pool that never refills. One growth unit "
            f"pays back {GROWTH_INCOME_PER_UNIT} each round."
        )
    events_left = len(run_state.schedule) - run_state.event_index
    return (
        f"You're in a steady position. The {label} should cost about {expected:.0f}; "
        f"{events_left} event(s) remain, so keep some resources in reserve."
    )


def render_mentor():
    toggle = document.getElementById("mentor-toggle")
    hint = document.getElementById("mentor-hint")
    toggle.checked = mentor_enabled
    hint.hidden = not mentor_enabled
    hint.innerText = f"\U0001F9ED Mentor: {mentor_suggestion(run)}" if mentor_enabled else ""


def on_toggle_mentor(event=None):
    global mentor_enabled
    mentor_enabled = document.getElementById("mentor-toggle").checked
    _storage_write(MENTOR_STORAGE_KEY, "1" if mentor_enabled else "0")
    render_mentor()


def on_toggle_past_runs(event=None):
    global past_runs_open
    past_runs_open = not past_runs_open
    render_past_runs_panel()


CATEGORY_ICON = {"weather": "🌦️", "non-weather": "🏗️", "social": "👥", "health": "🩺"}


def _render_event_breakdown_lines(container, event_log, show_category=False):
    for entry in event_log:
        line = document.createElement("p")
        line.className = (
            f"past-run-event event-category--{EVENT_CATEGORY[entry['type']]} "
            f"severity--{severity_label(entry['severity'])}"
        )
        category = EVENT_CATEGORY[entry["type"]]
        category_prefix = f"{CATEGORY_ICON[category]} " if show_category else ""
        if show_category:
            line.title = f"{category.replace('-', ' ')} event"
        line.innerText = (
            f"{category_prefix}{EVENT_ICON[entry['type']]} {EVENT_LABEL[entry['type']]} — "
            f"{entry['damage']:.0f} damage ({severity_label(entry['severity'])} intensity)"
        )
        container.appendChild(line)


def new_record_run_indexes():
    """E16: indexes into run_log_history of runs whose score beat every
    earlier run's (the first run is never a 'record' -- nothing to beat).
    Those cards get a one-shot CSS flourish when the panel is opened."""
    records = set()
    best = None
    for index, entry in enumerate(run_log_history):
        score = entry.get("score", 0)
        if best is not None and score > best:
            records.add(index)
        if best is None or score > best:
            best = score
    return records


# ---- E-22 / E-21 / E-20: notes, sort, filter, archive and compare in Past Runs ----
# All view state lives in memory (it is a way of looking at the list, not progress).
# The notes and the archive list live in `meta`, so they ride the progress export.
PAST_RUN_SORTS = ("newest", "oldest", "score_high", "score_low", "score_adjusted", "mode")
past_runs_sort = "newest"
past_runs_filter = "all"  # "all", "standard", "extended" or "scenario:<key>"
past_runs_show_archived = False
past_runs_compare = []  # up to two run numbers, oldest pick first


def run_mode(entry):
    """What kind of run a logged run was, worked out from its event log (the log has
    no scenario field): the scenario whose schedule it matches (or None) and whether it
    is an Extended Run (the schedule twice over)."""
    types = [e.get("type") for e in (entry.get("event_log") or []) if isinstance(e, dict)]
    custom = entry.get("custom_schedule")  # E-13: runs on a built schedule are tagged when logged
    if isinstance(custom, str) and custom:
        return {"scenario": None, "extended": False, "custom": custom}
    length = len(SCENARIOS[DEFAULT_SCENARIO]["schedule"])
    extended = len(types) == 2 * length and types[:length] == types[length:]
    base = types[:length] if extended else types
    scenario = next((key for key, spec in SCENARIOS.items() if spec["schedule"] == base), None)
    return {"scenario": scenario, "extended": extended}


def run_mode_label(entry):
    mode = run_mode(entry)
    if mode.get("custom"):
        return f"Custom schedule: {mode['custom']}"
    label = SCENARIOS[mode["scenario"]]["label"] if mode["scenario"] else "Custom schedule"
    return label + (", extended" if mode["extended"] else "")


def run_note(run_number):
    return meta["run_notes"].get(str(run_number), "")


def set_run_note(run_number, text):
    """E-22: keeps a short note for a completed run (cleared by an empty string)."""
    text = str(text or "").strip()[:RUN_NOTE_MAX_CHARS]
    if not text:
        meta["run_notes"].pop(str(run_number), None)
    elif str(run_number) in meta["run_notes"] or len(meta["run_notes"]) < RUN_NOTES_MAX:
        meta["run_notes"][str(run_number)] = text
    save_meta()
    return text


def set_run_archived(run_number, archived):
    """E-21: archiving only hides a run from the default list; its score, its knowledge
    points and every stat built from it are untouched."""
    current = set(meta["archived_runs"])
    if archived:
        current.add(run_number)
    else:
        current.discard(run_number)
    meta["archived_runs"] = sorted(current)
    save_meta()


def past_runs_view(history=None):
    """The run log entries that pass the current filter, in the current sort order
    (each as (position in run_log_history, entry))."""
    history = run_log_history if history is None else history
    archived = set(meta["archived_runs"])
    rows = []
    for index, entry in enumerate(history):
        if not isinstance(entry, dict) or "run_number" not in entry:
            continue
        if entry["run_number"] in archived and not past_runs_show_archived:
            continue
        mode = run_mode(entry)
        if past_runs_filter == "custom" and not (mode.get("custom") or mode["scenario"] is None):
            continue
        if past_runs_filter == "extended" and not mode["extended"]:
            continue
        if past_runs_filter == "standard" and mode["extended"]:
            continue
        if past_runs_filter.startswith("scenario:") and mode["scenario"] != past_runs_filter.split(":", 1)[1]:
            continue
        rows.append((index, entry))
    if past_runs_sort == "oldest":
        rows.sort(key=lambda r: r[0])
    elif past_runs_sort == "score_high":
        rows.sort(key=lambda r: (-r[1].get("score", 0), -r[0]))
    elif past_runs_sort == "score_low":
        rows.sort(key=lambda r: (r[1].get("score", 0), -r[0]))
    elif past_runs_sort == "score_adjusted":  # E-9
        rows.sort(key=lambda r: (-adjusted_score(r[1].get("score", 0), r[1].get("event_log")), -r[0]))
    elif past_runs_sort == "mode":
        rows.sort(key=lambda r: (run_mode_label(r[1]), -r[0]))
    else:
        rows.sort(key=lambda r: -r[0])
    return rows


def _run_by_number(run_number):
    for entry in run_log_history:
        if isinstance(entry, dict) and entry.get("run_number") == run_number:
            return entry
    return None


def compare_runs_rows(entry_a, entry_b):
    """E-20: the two runs side by side: a header row, a stats row each for score, damage,
    resilience, growth and knowledge (with the difference), then the events in order with
    the damage difference on the one that was harsher."""
    rows = []
    for label, key, fmt in (
        ("Score", "score", "{:.0f}"),
        ("Damage taken", "damage_taken", "{:.0f}"),
        ("Resilience", "resilience_capacity", "{:.0f}"),
        ("Growth", "growth_capacity", "{:.0f}"),
        ("Knowledge earned", "knowledge_earned", "{:.0f}"),
    ):
        a, b = entry_a.get(key, 0), entry_b.get(key, 0)
        diff = b - a
        sign = "+" if diff > 0 else "\u2212"
        change = f" ({sign}{fmt.format(abs(diff))})" if abs(diff) >= 0.5 else " (same)"
        rows.append({
            "kind": "stat",
            "left": f"{label}: {fmt.format(a)}",
            "right": f"{label}: {fmt.format(b)}{change}",
            "different": abs(diff) >= 0.5,
        })
    log_a, log_b = entry_a.get("event_log") or [], entry_b.get("event_log") or []
    for position in range(max(len(log_a), len(log_b))):
        ea = log_a[position] if position < len(log_a) else None
        eb = log_b[position] if position < len(log_b) else None

        def describe(event, other):
            if event is None:
                return "(no event)"
            text = f"{position + 1}. {EVENT_ICON[event['type']]} {EVENT_LABEL[event['type']]}: {event['damage']:.0f} damage"
            if other is not None and other["type"] == event["type"] and abs(event["damage"] - other["damage"]) >= 0.5:
                text += " (harsher)" if event["damage"] > other["damage"] else " (gentler)"
            elif other is not None and other["type"] != event["type"]:
                text += " (different event)"
            return text

        rows.append({
            "kind": "event",
            "left": describe(ea, eb),
            "right": describe(eb, ea),
            "different": ea is None or eb is None or ea["type"] != eb["type"] or abs(ea["damage"] - eb["damage"]) >= 0.5,
        })
    return rows


def compare_summary_text(entry_a, entry_b):
    diff = entry_b.get("score", 0) - entry_a.get("score", 0)
    if abs(diff) < 0.5:
        return f"Run #{entry_a['run_number']} and Run #{entry_b['run_number']} finished with the same score."
    better, worse = (entry_b, entry_a) if diff > 0 else (entry_a, entry_b)
    return f"Run #{better['run_number']} scored {abs(diff):.0f} more than Run #{worse['run_number']}."


def render_past_run_compare():
    box = document.getElementById("past-runs-compare")
    if box is None:
        return
    box.innerHTML = ""
    entries = [_run_by_number(n) for n in past_runs_compare]
    entries = [e for e in entries if e is not None]
    if len(entries) < 2:
        box.hidden = True
        return
    box.hidden = False
    entry_a, entry_b = entries[0], entries[1]
    heading = document.createElement("p")
    heading.className = "past-run-title"
    heading.innerText = "Side by side: " + compare_summary_text(entry_a, entry_b)
    box.appendChild(heading)
    grid = document.createElement("div")
    grid.className = "compare-grid"
    for entry in (entry_a, entry_b):
        head = document.createElement("p")
        head.className = "compare-head"
        head.innerText = f"Run #{entry['run_number']} ({run_mode_label(entry)})"
        grid.appendChild(head)
    for row in compare_runs_rows(entry_a, entry_b):
        for side in ("left", "right"):
            cell = document.createElement("p")
            cell.className = f"compare-cell compare-cell--{row['kind']}" + (" compare-cell--different" if row["different"] else "")
            cell.innerText = row[side]
            grid.appendChild(cell)
    box.appendChild(grid)


def streak_log_indexes():
    """GE-22: positions in run_log_history that belong to the current improvement streak
    (empty below STREAK_MIN)."""
    scores = [e.get("score", 0) for e in run_log_history if isinstance(e, dict)]
    streak = improvement_streak(scores)
    if streak < STREAK_MIN:
        return set()
    return set(range(len(scores) - streak, len(scores)))


def _past_run_card(index, entry, is_record):
    run_number = entry["run_number"]
    card = document.createElement("div")
    card.className = "past-run-card past-run-card--record" if is_record else "past-run-card"
    if run_number in meta["archived_runs"]:
        card.className += " past-run-card--archived"
    if index in streak_log_indexes():
        card.className += " past-run-card--streak"
    title = document.createElement("p")
    title.className = "past-run-title"
    title.innerText = (
        f"{'🏆 ' if is_record else ''}{'🔥 ' if index in streak_log_indexes() else ''}Run #{run_number} — score {entry['score']:.0f} "
        f"({adjusted_text(entry['score'], entry.get('event_log'))}; resilience {entry['resilience_capacity']}, growth {entry['growth_capacity']}, "
        f"+{entry['knowledge_earned']} knowledge)"
        f" · {run_mode_label(entry)}" + (" · archived" if run_number in meta["archived_runs"] else "")
    )
    card.appendChild(title)
    _render_event_breakdown_lines(card, entry["event_log"], show_category=True)
    note = document.createElement("input")
    note.className = "past-run-note-input"
    note.setAttribute("type", "text")
    note.setAttribute("maxlength", str(RUN_NOTE_MAX_CHARS))
    note.setAttribute("placeholder", "Add a note about this run")
    note.setAttribute("aria-label", f"Note for run {run_number}")
    note.setAttribute("data-action", "note")
    note.setAttribute("data-run", str(run_number))
    note.value = run_note(run_number)
    card.appendChild(note)
    actions = document.createElement("div")
    actions.className = "past-run-actions"
    compare_label = document.createElement("label")
    compare_label.className = "past-run-compare-label"
    compare_box = document.createElement("input")
    compare_box.setAttribute("type", "checkbox")
    compare_box.setAttribute("data-action", "compare")
    compare_box.setAttribute("data-run", str(run_number))
    compare_box.checked = run_number in past_runs_compare
    compare_label.appendChild(compare_box)
    compare_text = document.createElement("span")
    compare_text.innerText = " Compare"
    compare_label.appendChild(compare_text)
    actions.appendChild(compare_label)
    archive_button = document.createElement("button")
    archive_button.className = "secondary past-run-archive-button"
    archive_button.setAttribute("type", "button")
    archive_button.setAttribute("data-action", "archive")
    archive_button.setAttribute("data-run", str(run_number))
    archive_button.innerText = "Unarchive" if run_number in meta["archived_runs"] else "Archive"
    actions.appendChild(archive_button)
    card.appendChild(actions)
    return card


# ---- GE-22: run-improvement streak --------------------------------------------
STREAK_MIN = 2


def record_flags(scores):
    """For each score in completion order: did it beat every earlier run? (The first
    run has nothing to beat, so it is never a record.)"""
    flags, best = [], None
    for score in scores:
        flags.append(best is not None and score > best)
        if best is None or score > best:
            best = score
    return flags


def improvement_streak(scores):
    """How many of the most recent runs, in a row, each beat the best before them."""
    count = 0
    for flag in reversed(record_flags(scores)):
        if not flag:
            break
        count += 1
    return count


def streak_text(scores=None):
    scores = run_history if scores is None else scores
    streak = improvement_streak(scores)
    if streak < STREAK_MIN:
        return ""
    return f"\U0001F525 Improvement streak: {streak} runs in a row beat your previous best."


def render_past_runs_panel():
    toggle = document.getElementById("past-runs-toggle-button")
    panel = document.getElementById("past-runs-panel")
    toggle.innerText = "Hide Past Runs" if past_runs_open else f"📜 Review Past Runs ({len(run_log_history)})"
    panel.hidden = not past_runs_open
    if not past_runs_open:
        return
    listing = document.getElementById("past-runs-list")
    controls = document.getElementById("past-runs-controls")
    if listing is None:
        return  # a cached older page without the list container
    listing.innerHTML = ""
    if controls is not None:
        controls.hidden = not run_log_history
    render_past_run_compare()
    if not run_log_history:
        empty = document.createElement("p")
        empty.innerText = "No detailed run history yet — complete a run to start building one."
        listing.appendChild(empty)
        return

    record_indexes = new_record_run_indexes()
    rows = past_runs_view()
    status = document.getElementById("past-runs-status")
    if status is not None:
        hidden_count = len(run_log_history) - len(rows)
        status.innerText = f"Showing {len(rows)} of {len(run_log_history)} runs." + (
            " Archived and filtered-out runs keep their score and knowledge." if hidden_count else ""
        )
    if not rows:
        empty = document.createElement("p")
        empty.innerText = "No runs match this view. Change the filter or show archived runs."
        listing.appendChild(empty)
        return
    for index, entry in rows:
        listing.appendChild(_past_run_card(index, entry, index in record_indexes))


def on_past_runs_event(event=None):
    """One delegated handler for everything inside the Past Runs list: the note boxes, the
    Compare ticks and the Archive buttons (cards are rebuilt on every render, so a handler
    per card would pile up)."""
    global past_runs_compare
    target = getattr(event, "target", None)
    if target is None:
        return
    action = target.getAttribute("data-action")
    raw_run = target.getAttribute("data-run")
    if not action or raw_run is None or not str(raw_run).isdigit():
        return
    run_number = int(raw_run)
    if action == "note":
        set_run_note(run_number, target.value)
    elif action == "archive":
        set_run_archived(run_number, run_number not in meta["archived_runs"])
        render()
    elif action == "compare":
        if target.checked:
            if run_number not in past_runs_compare:
                past_runs_compare = (past_runs_compare + [run_number])[-2:]
        else:
            past_runs_compare = [n for n in past_runs_compare if n != run_number]
        render()


def on_past_runs_controls_change(event=None):
    global past_runs_sort, past_runs_filter, past_runs_show_archived
    sort_el = document.getElementById("past-runs-sort")
    filter_el = document.getElementById("past-runs-filter")
    archived_el = document.getElementById("past-runs-archived")
    if sort_el is not None and sort_el.value in PAST_RUN_SORTS:
        past_runs_sort = sort_el.value
    if filter_el is not None:
        value = filter_el.value
        if value in ("all", "standard", "extended", "custom") or (value.startswith("scenario:") and value.split(":", 1)[1] in SCENARIOS):
            past_runs_filter = value
    if archived_el is not None:
        past_runs_show_archived = bool(archived_el.checked)
    render()


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as SOL/Canopy/Grid's reference
# achievements integration -- a flat JSON catalog fetched into the Pyodide
# boot sequence and handed to Python as a window global (see index.html),
# rendered into a hidden-until-opened panel. Unlike achievements.json this
# catalog isn't a set of checkable conditions -- it's just curated highlight
# text -- so there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS below, since a "what's
# new" panel is additive, not core to Aftermath's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
except Exception:
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


# ===========================================================================
# E8/E16: an "expected damage this event" preview, with the underlying
# severity multiplier shown numerically rather than just mild/typical/
# severe -- both derived from the exact same deterministic formula
# resolve_next_event() itself will use, so the preview is exact, not a
# rough estimate.
# ===========================================================================
def expected_next_event_damage(run_state):
    """Returns (damage, severity) for run_state's next scheduled event, or
    None once the run is already complete."""
    if run_state.is_complete():
        return None
    event_type = run_state.next_event_type()
    severity = run_state.severity_at(run_state.event_index)
    damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - run_state.mitigation_for(event_type))
    return damage, severity


def expected_damage_range(run_state):
    """E14: (low, high) damage for the next event across the whole
    severity band this settlement can face (min/max multiplier at the
    current skill level and career length). The center estimate above is
    exact for this run number; the range shows how much a different run
    number could swing the same event."""
    event_type = run_state.next_event_type()
    if run_state.normalised:
        # E-4: the draw is fixed, so the number is exact.
        exact = EVENT_BASE_DAMAGE[event_type] * run_state.severity_at(run_state.event_index) * (1 - run_state.mitigation_for(event_type))
        return exact, exact
    if run_state.run_number <= 1:
        exact = EVENT_BASE_DAMAGE[event_type] * (1 - run_state.mitigation_for(event_type))
        return exact, exact
    low_sev, high_sev = severity_bounds(skill_tree_strength())
    base = EVENT_BASE_DAMAGE[event_type] * (1 - run_state.mitigation_for(event_type))
    return base * low_sev, base * high_sev


def severity_tooltip_text(run_number):
    """E20: how skill-tree strength (and career length) affect severity."""
    strength = skill_tree_strength()
    low, high = severity_bounds(strength)
    if run_number <= 1:
        return "Run 1 is always exactly 1.00× severity. From run 2 onward, severity varies per event."
    return (
        f"Severity multiplier varies between {low:.2f}× and {high:.2f}×. Base spread is 0.85×–1.15×; "
        f"each unlocked skill (you have {strength}) widens it by {SEVERITY_VARIATION_RANGE_PER_SKILL:.2f} "
        f"each side, and each completed run adds a little more (up to {SEVERITY_LIFETIME_RANGE_CAP:.2f}). "
        f"The center stays 1.00× — a stronger tree faces bigger swings, not a higher average."
    )


last_knowledge_preview = None


# ===========================================================================
# E17: "toughest run yet" -- the lowest-scoring completed run. run_history
# is a flat list of scores in completion order (no run_number stored
# alongside each), so the displayed "Run #N" is that run's *position* in
# the list, not necessarily its literal run_number -- these coincide for
# the overwhelmingly common case (runs completed in strict numeric order)
# and only diverge in the rare stale-reload edge case the save-system
# double-award guard already documents elsewhere in this file. Good enough
# for a flavor comparison; run_log_history (E7) has the exact run_number
# for any run a player wants to inspect precisely.
# ===========================================================================
def toughest_run_yet():
    if not run_history:
        return None
    worst_score = min(run_history)
    return run_history.index(worst_score) + 1, worst_score


def toughest_run_sequence():
    """E10: the event sequence of the toughest run yet, as a list of
    {"type", "damage", "severity"} dicts, pulled from run_log_history (the
    detailed per-run log) by matching the toughest score. None if there's
    no detailed log for it (e.g. progress imported from a code, which
    carries scores only)."""
    toughest = toughest_run_yet()
    if toughest is None:
        return None
    for entry in run_log_history:
        if abs(entry.get("score", -1) - toughest[1]) < 1e-9 and entry.get("event_log"):
            return entry["event_log"]
    return None


def toughest_run_text():
    toughest = toughest_run_yet()
    if toughest is None:
        return ""
    text = f"Toughest run yet: Run #{toughest[0]} scored {toughest[1]:.0f}"
    sequence = toughest_run_sequence()
    if sequence:
        text += f" ({adjusted_text(toughest[1], sequence)})"  # E-9
    if sequence:
        parts = [f"{EVENT_ICON[e['type']]} {EVENT_LABEL[e['type']]}" for e in sequence if e["type"] in EVENT_LABEL]
        text += " — " + " → ".join(parts)
    return text


def average_severity(event_log):
    if not event_log:
        return 1.0
    return sum(e.get("severity", 1.0) for e in event_log) / len(event_log)


def _report_hardest_schedule(run_state):
    """E23: a run that ended with resources left feeds its average event
    severity to the shared opt-in leaderboard widget (which only submits for
    an opted-in, signed-in player and remembers the personal best). Run 1 is
    always exactly 1.00x, so only the harsher later runs can climb the board."""
    if run_state.resources <= 0 or not run_state.event_log:
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    board = getattr(window, "NoyvjLeaderboard", None)
    if board is not None:
        board.report(
            "aftermath", "hardest_schedule", round(average_severity(run_state.event_log), 3),
            f"run {run_state.run_number}",
        )


def toughest_survived_run_badge_earned():
    """E12: a settlement-art badge for having come through a run whose
    average event severity was harsh ('severe' band) without ending at zero
    resources -- a personal-best-style marker for surviving a genuinely
    tough schedule, separate from the per-skill badges."""
    for entry in run_log_history:
        if entry.get("score", 0) > 0 and severity_label(average_severity(entry.get("event_log", []))) == "severe":
            return True
    return False


def toughest_badge_title():
    """E-9: the badge's tooltip. Earned: names the run and shows the raw and adjusted score;
    not yet: says what earns it."""
    for entry in run_log_history:
        if entry.get("score", 0) > 0 and severity_label(average_severity(entry.get("event_log", []))) == "severe":
            return (
                f"Survived a run at severe average intensity: run {entry.get('run_number', '?')} scored "
                f"{entry['score']:.0f} ({adjusted_text(entry['score'], entry.get('event_log'))})"
            )
    return "Survived a run at severe average intensity (not earned yet)"


def runs_completed_text():
    name = meta["settlement_name"]
    prefix = f"{name} — " if name else ""
    return f"{prefix}Runs completed: {len(run_history)}"


# E30a/E30b: "X runs until affordable" estimate + pinned skills.
def average_knowledge_per_run():
    runs = len(run_history)
    if runs <= 0:
        return None
    return skill_tree.lifetime_knowledge / runs


def runs_until_affordable(skill_id):
    """Estimated number of further completed runs before skill_id becomes
    affordable at the average lifetime knowledge-earn rate. 0 if already
    affordable, None if there's no earn-rate data yet (no runs completed)."""
    needed = SKILLS[skill_id]["cost"] - skill_tree.knowledge_points
    if needed <= 0:
        return 0
    rate = average_knowledge_per_run()
    if not rate or rate <= 0:
        return None
    return max(1, math.ceil(needed / rate))


def _eta_text(skill_id):
    runs = runs_until_affordable(skill_id)
    if runs is None:
        return "Complete a run for an estimate"
    if runs == 0:
        return "Affordable now"
    return f"~{runs} run{'s' if runs != 1 else ''} until affordable"


def toggle_pin_skill(skill_id):
    if skill_id not in SKILLS or skill_id in skill_tree.unlocked:
        return False
    if skill_id in meta["pinned_skills"]:
        meta["pinned_skills"].remove(skill_id)
    else:
        meta["pinned_skills"].append(skill_id)
    save_meta()
    return True


def pinned_skills_text():
    pinned = [sid for sid in meta["pinned_skills"] if sid in SKILLS and sid not in skill_tree.unlocked]
    if not pinned:
        return ""
    return "📌 Saving toward: " + "; ".join(f"{SKILLS[sid]['label']} ({_eta_text(sid)})" for sid in pinned)


def set_settlement_name(name):
    meta["settlement_name"] = (name or "").strip()[:SETTLEMENT_NAME_MAX]
    save_meta()


# ===========================================================================
# E12: export/import code for the localStorage-based skill tree, run
# history, legacy system, and achievement progress -- everything this
# game persists *outside* the per-run save-widget round trip (see
# get_state()/load_state()'s own big comment below for why those two
# mechanisms are kept separate). A base64-wrapped JSON blob, the same
# shape as the shared save widget's own codes, but carrying this game's
# cross-run progress instead of one run's live state.
# ===========================================================================
PROGRESS_EXPORT_VERSION = 1


def export_progress_code():
    bundle = {
        "version": PROGRESS_EXPORT_VERSION,
        "skill_tree": skill_tree.to_dict(),
        "run_history": list(run_history),
        "legacy_events": sorted(legacy_events),
        "legacy_event_counts": dict(legacy_event_counts),
        "achievement_progress": dict(achievement_progress),
        "highest_awarded_run": highest_awarded_run,
        "meta": dict(meta),
    }
    # Z8: codec now lives in shared/export_progress.py (the "portable
    # progress-code" pattern shared with SOL's A17) -- no prefix, matching
    # this code's original plain-base64 shape (no existing player-held
    # code has a tag to check against, so adding one now would just be
    # decoration).
    return export_progress.encode_progress_code(bundle)


def import_progress_code(code):
    """Parses and applies a code from export_progress_code(). Returns True
    on success, False on any malformed input -- unlike load_state() below
    (which deliberately raises on a bad payload, since that one only ever
    receives this same site's own save codes), a progress code is
    hand-typed/pasted by a player and a bad paste is an expected, common
    failure mode that should fail soft with a status message, not crash
    the page."""
    global skill_tree, run_history, legacy_events, legacy_event_counts, achievement_progress, highest_awarded_run, meta

    ok, bundle = export_progress.decode_progress_code(code)
    if not ok or "skill_tree" not in bundle:
        return False

    try:
        st_data = bundle["skill_tree"]
        new_skill_tree = SkillTreeState()
        new_skill_tree.knowledge_points = st_data.get("knowledge_points", 0)
        new_skill_tree.unlocked = set(st_data.get("unlocked", []))
        new_skill_tree.lifetime_knowledge = st_data.get("lifetime_knowledge", new_skill_tree.knowledge_points)

        new_run_history = list(bundle.get("run_history", []))
        new_legacy_events = set(bundle.get("legacy_events", []))
        new_legacy_event_counts = {
            str(k): int(v) for k, v in dict(bundle.get("legacy_event_counts", {})).items()
        }
        new_achievement_progress = _default_achievement_progress()
        for key, value in dict(bundle.get("achievement_progress", {})).items():
            if key in new_achievement_progress:
                new_achievement_progress[key] = bool(value)
        new_highest_awarded_run = int(bundle.get("highest_awarded_run", 0))
    except (ValueError, TypeError, AttributeError):
        return False

    skill_tree = new_skill_tree
    run_history = new_run_history
    legacy_events = new_legacy_events
    legacy_event_counts = new_legacy_event_counts
    achievement_progress = new_achievement_progress
    highest_awarded_run = new_highest_awarded_run
    meta = _sanitize_meta(bundle.get("meta", {}))
    save_meta()

    skill_tree.save()
    save_run_history(run_history)
    save_legacy_events(legacy_events)
    save_legacy_event_counts(legacy_event_counts)
    save_achievement_progress()
    save_highest_awarded_run(highest_awarded_run)
    _seed_achievement_toast_baseline()
    return True


def progress_summary_text():
    """E26: a short human-readable summary of what an exported progress
    code contains, shown before the player copies it."""
    best = f", best score {max(run_history):.0f}" if run_history else ""
    earned = len(achievement_ids_earned())
    name = f"Settlement \"{meta['settlement_name']}\": " if meta["settlement_name"] else ""
    return (
        f"{name}{len(run_history)} run{'s' if len(run_history) != 1 else ''} completed{best}, "
        f"{len(skill_tree.unlocked)}/{len(SKILLS)} skills unlocked, "
        f"{skill_tree.knowledge_points} knowledge in hand ({skill_tree.lifetime_knowledge} lifetime), "
        f"{earned} achievement{'s' if earned != 1 else ''}."
    )


def on_export_progress(event=None):
    document.getElementById("progress-export-output").value = export_progress_code()
    document.getElementById("progress-code-status").innerText = (
        "Progress code generated below — copy it somewhere safe. Contains: " + progress_summary_text()
    )


def on_import_progress(event=None):
    code = document.getElementById("progress-import-input").value
    status = document.getElementById("progress-code-status")
    if not code or not code.strip():
        status.innerText = "Paste a progress code first."
        return
    if import_progress_code(code):
        status.innerText = "Progress imported successfully."
        render()
    else:
        status.innerText = "That code couldn't be read — check you copied the whole thing."


# ===========================================================================
# E13: reset skill tree.
#
# Z22 cross-game audit: this used to be gated behind a lightweight in-UI
# two-click confirmation (click once to arm, click again to actually
# reset) rather than a browser confirm() dialog -- chosen at the time to
# stay self-contained in the fake-DOM test harness with no new `window`
# global needed, and any other skill-tree/run action cleared the pending
# confirmation so a stray click much later couldn't accidentally fire it.
# shared/confirm-dialog.js didn't exist yet when that was written; now
# that it does (and every other game's own reset/retire-style action
# already routes through it -- Grid's retire-last-plant, Herd's pivot
# investment, Loop's Start New Chain, Trade Empire's automate/research,
# SOL's reset-world/prestige), migrated to match: a real modal is a
# stronger affordance than a button whose label silently changes meaning
# after the first click, offers "don't ask me again," and doesn't block
# on some *other* button being clicked first to "escape" a still-armed
# reset the way the two-click version could. `_confirm_dialog_ask()` is
# the same helper shape as every other game's own copy.
# ===========================================================================
def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=None):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    options = {} if allow_skip is None else {"allowSkip": allow_skip}
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
        **options,
    )


def reset_refund_amount():
    """E22: knowledge points a reset would refund from *spent* skills --
    what the confirm dialog's message shows before you commit."""
    return sum(SKILLS[skill_id]["cost"] for skill_id in skill_tree.unlocked)


def reset_refund_total():
    return skill_tree.knowledge_points + reset_refund_amount()


def reset_skill_tree():
    """Refunds every spent-and-unspent knowledge point (so respeccing
    doesn't punish a player for having unlocked anything) and clears which
    skills are unlocked. lifetime_knowledge (the achievement-tracking
    total) is deliberately untouched -- it's a lifetime-earned counter,
    not a spendable balance, so a respec shouldn't roll it back."""
    total_refund = reset_refund_total()
    skill_tree.knowledge_points = total_refund
    skill_tree.unlocked = set()
    skill_tree.save()


def on_reset_skill_tree(event=None):
    if not skill_tree.unlocked:
        return  # nothing to lose -- render()'s own disabled-state already guards this too

    def _do_reset():
        reset_skill_tree()
        render()

    _confirm_dialog_ask(
        action_id="aftermath-reset-skill-tree",
        message=(
            f"Reset the skill tree? This refunds all {reset_refund_total()} knowledge points "
            "spent and unspent, and clears every unlocked skill. Your lifetime knowledge total "
            "is not affected. This cannot be undone."
        ),
        confirm_label="Reset skill tree",
        on_confirm=_do_reset,
    )


# ===========================================================================
# E14: a dedicated toast surfacing a skill's real-world grounding text
# prominently at the moment it's unlocked -- the always-visible
# `skill-practice` paragraph in the skill tree already shows this text,
# but this makes it impossible to miss on the exact unlock that made it
# relevant.
# ===========================================================================
SKILL_TOAST_BASE_MS = 4000
SKILL_TOAST_MS_PER_CHAR = 35
SKILL_TOAST_MIN_MS = 6000
SKILL_TOAST_MAX_MS = 14000


def skill_toast_duration_ms(skill_id):
    """E2: longer grounding text stays up longer -- a fixed base plus a
    per-character reading allowance, clamped so no toast is ever gone
    faster than the old fixed 6s or lingers past 14s."""
    length = len(SKILLS[skill_id]["real_practice"])
    return max(SKILL_TOAST_MIN_MS, min(SKILL_TOAST_MAX_MS, SKILL_TOAST_BASE_MS + SKILL_TOAST_MS_PER_CHAR * length))


def _display_skill_unlock_toast(skill_id):
    skill = SKILLS[skill_id]
    toast = document.getElementById("skill-unlock-toast")
    text = document.getElementById("skill-unlock-toast-text")
    text.innerText = f"🔓 {skill['label']} unlocked — {skill['real_practice']}"
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, skill_toast_duration_ms(skill_id))


# ===========================================================================
# E10: a brief, self-clearing visual flash on the resources readout when
# an investment is actually spent -- confirmation feedback beyond the
# number itself changing. Reuses the same create_proxy/setTimeout
# one-shot-timer pattern as the achievement/skill-unlock toasts above.
# ===========================================================================
def _flash_element(element_id, duration_ms=400, css_class="invest-flash"):
    element = document.getElementById(element_id)
    element.classList.add(css_class)

    def _remove(*args):
        element.classList.remove(css_class)
        proxy.destroy()

    proxy = create_proxy(_remove)
    setTimeout(proxy, duration_ms)


# ===========================================================================
# One-time callouts (E8 first-zero-score reassurance, E28 first harsher-than-
# base severity swing). A shared #callout-display line; the "already shown"
# flags persist in `meta` so each fires once per browser, ever. The message
# itself is transient (cleared when a new run starts).
# ===========================================================================
callout_message = ""

NEGATIVE_RUN_TIP = (
    "💡 That run ended with nothing left — but nothing is lost. Your skill tree persists "
    "regardless: you still earned at least 1 knowledge point, and every skill you've unlocked "
    "carries into the next run."
)
HARSH_SEVERITY_CALLOUT = (
    "💡 That event hit harder than a first-run event ever could. This isn't bad luck — the more skills "
    "you've unlocked (and the more runs you've completed), the wider the severity spread gets: a "
    "stronger settlement is asked bigger questions, on top of being better equipped to answer them."
)


def _maybe_trigger_callouts(run_state):
    global callout_message
    if run_state.event_log:
        last = run_state.event_log[-1]
        if not meta["seen_harsh_callout"] and last["severity"] > SEVERITY_VARIATION_MAX:
            meta["seen_harsh_callout"] = True
            save_meta()
            callout_message = HARSH_SEVERITY_CALLOUT
    if run_state.is_complete() and run_state.resources <= 0 and not meta["seen_negative_tip"]:
        meta["seen_negative_tip"] = True
        save_meta()
        callout_message = NEGATIVE_RUN_TIP


# E5: "generational memory" -- occasionally the upcoming event's flavor
# references what the same slot cost a past run, deepening the legacy system.
def generational_memory_text(run_state):
    if run_state.is_complete() or not run_log_history:
        return ""
    if (run_state.run_number + run_state.event_index) % 2 != 0:
        return ""
    index = run_state.event_index
    for entry in reversed(run_log_history):
        if entry.get("run_number") == run_state.run_number:
            continue
        log = entry.get("event_log", [])
        if index < len(log) and log[index]["type"] == run_state.next_event_type():
            past = log[index]
            return (
                f"🕰️ Memory of Run #{entry['run_number']}: the last time this settlement faced "
                f"{EVENT_LABEL[past['type']]} at this point, it cost {past['damage']:.0f} damage."
            )
    return ""


# E13: a short narrative epilogue at the end of an extended run, in the
# spirit of Continuum's era-transition beats, scaled to Aftermath's format.
def extended_epilogue_text(run_state):
    if not run_state.extended or not run_state.is_complete():
        return ""
    if run_state.resources <= 0:
        return (
            "Epilogue — Two full cycles of shocks left the settlement with nothing in reserve. "
            "But the people are still here, and what they learned is written into every plan that follows."
        )
    if run_state.resources > run_state.starting_resources:
        return (
            "Epilogue — Fourteen shocks came and went, and the settlement ended richer than it began. "
            "What once felt like recovery has become routine: a community that expects the next storm and is ready for it."
        )
    return (
        "Epilogue — The settlement came through fourteen shocks bruised but standing. "
        "Endurance is its own kind of progress: the next generation inherits a place that has already been tested."
    )


# ===========================================================================
# W2-aftermath -- "In the real world": for each kind of shock, one real
# recovery or response, with the source named and linked. Every figure was read
# from the linked page on 2026-09-26 (nothing recalled from memory); where a
# page did not give a number, none is quoted. The note follows the event you
# last faced, or the next one before the first event, and never changes any
# number in a run.
# ===========================================================================
REAL_WORLD_READ_DATE = "2026-09-26"
REAL_WORLD_EXAMPLES = {
    "flood": {
        "title": "Room for the River (Netherlands)",
        "text": "After floods in 1993 and 1995 forced the evacuation of over 200,000 people, the Netherlands ran a programme from 2006 to 2015 with a budget of 2.2 billion euros, about forty projects, to give its rivers more space rather than only raising dikes.",
        "source": "Wikipedia, Room for the River", "url": "https://en.wikipedia.org/wiki/Room_for_the_River",
    },
    "heatwave": {
        "title": "France's National Heat Wave Plan",
        "text": "The 2003 European heat wave is estimated to have killed more than 70,000 people, including 14,802 in France, mostly elderly. The following year France drew up a National Heat Wave Plan built on forecasting and alert systems.",
        "source": "Wikipedia, 2003 European heat wave", "url": "https://en.wikipedia.org/wiki/2003_European_heat_wave",
    },
    "storm": {
        "title": "Bangladesh's Cyclone Preparedness Programme",
        "text": "Set up in 1973 as an early-warning system for coastal Bangladesh, the programme now has 55 thousand volunteers who carry warnings to villages, and is credited with saving thousands of lives.",
        "source": "Wikipedia, Cyclone Preparedness Programme", "url": "https://en.wikipedia.org/wiki/Cyclone_Preparedness_Programme",
    },
    "supply_chain": {
        "title": "The 2021 Suez Canal blockage",
        "text": "One grounded ship blocked the canal for six days, 23 to 29 March 2021. By 28 March at least 369 ships were queuing, and Lloyd's List calculated about 9.6 billion dollars of goods a day was held up.",
        "source": "Wikipedia, 2021 Suez Canal obstruction", "url": "https://en.wikipedia.org/wiki/2021_Suez_Canal_obstruction",
    },
    "infrastructure_failure": {
        "title": "The 2003 Northeast blackout",
        "text": "On 14 August 2003 a software bug that stalled a control room's alarm system for over an hour let a local fault cascade, and 55 million people in Ontario and eight US states lost power, for between two hours and four days depending on where they lived.",
        "source": "Wikipedia, Northeast blackout of 2003", "url": "https://en.wikipedia.org/wiki/Northeast_blackout_of_2003",
    },
    "civil_unrest": {
        "title": "Christchurch's Student Volunteer Army",
        "text": "After the 2010 and 2011 Christchurch earthquakes strained the city, a student-started volunteer effort grew to 13,000 students a week at its peak and helped clear over 360,000 tonnes of silt, showing how community cooperation can be rebuilt fast.",
        "source": "Wikipedia, Student Volunteer Army", "url": "https://en.wikipedia.org/wiki/Student_Volunteer_Army",
    },
    # FY-3: read live on 2026-10-09 (a later read than the six above, so it carries its own date).
    "heat_mortality": {
        "title": "The 1995 Chicago heat wave",
        "text": "The heat wave caused 739 heat-related deaths in Chicago over five days, mostly elderly poor residents, some without air conditioning and others unable to afford to run it. City officials did not release a heat emergency warning until the last day, so the city's five cooling centres were not fully used.",
        "source": "Wikipedia, 1995 Chicago heat wave", "url": "https://en.wikipedia.org/wiki/1995_Chicago_heat_wave",
        "read": "2026-10-09",
    },
}


def real_world_event_type():
    """The event type the note is about: the last one faced, else the next."""
    if run.event_log:
        return run.event_log[-1]["type"]
    if run.event_index < len(run.schedule):
        return run.schedule[run.event_index]
    return None


def render_real_world():
    box = document.getElementById("real-world-note")
    example = REAL_WORLD_EXAMPLES.get(real_world_event_type())
    box.hidden = example is None
    if example is None:
        return
    document.getElementById("real-world-text").innerText = f"In the real world: {example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {example.get('read', REAL_WORLD_READ_DATE)})"
    link.href = example["url"]


# ===========================================================================
# Round-3 additions (planning/TODO.md "GE + E. Aftermath", 2026-10-07):
# E-12 Disaster Codex, E-1 lifetime statistics, E-15 x1/x5/Max steps,
# GE-18 undo, GE-15 Flawless Defense (rules live in RunState above),
# GE-13 prevented-damage popup, E-23 knowledge itemisation, E-24 copy run
# summary, E-27 live tab title, E-5 (partial) aria-live announcements.
# None of this changes a rule that existed before except the Flawless
# Defense bonus point.
# ===========================================================================

# ---- E-15: invest step size (x1 / x5 / Max), remembered per browser -------
INVEST_STEP_STORAGE_KEY = "aftermath-invest-step"
INVEST_STEPS = (1, 5, "max")


def load_invest_step():
    raw = localStorage.getItem(INVEST_STEP_STORAGE_KEY)
    if raw == "max":
        return "max"
    if raw in ("1", "5"):
        return int(raw)
    return 1


invest_step = load_invest_step()


def set_invest_step(value):
    global invest_step
    if value not in INVEST_STEPS:
        return False
    invest_step = value
    _storage_write(INVEST_STEP_STORAGE_KEY, str(value))
    return True


def step_label(step):
    return "Max" if step == "max" else f"x{step}"


def resilience_button_label(run_state, step):
    units = run_state.step_units("resilience", step)
    if step == 1 or units < 1:
        return f"Invest in Resilience ({RESILIENCE_COST})"
    return f"Invest in Resilience x{units} ({RESILIENCE_COST * units})"


def growth_step_label(run_state, step):
    units = run_state.step_units("growth", step)
    if step == 1 or units < 1:
        return growth_button_label(run_state.growth_capacity)
    return growth_button_label(run_state.growth_capacity, units)


# ---- E-12 / E-1: records across every run -------------------------------
def lifetime_event_records():
    """Every event faced that a log remembers: all completed runs'
    event_logs plus the run in progress (a finished run is already in
    run_log_history once it pays out)."""
    records = []
    for entry in run_log_history:
        if not isinstance(entry, dict):
            continue
        for event in entry.get("event_log", []) or []:
            if isinstance(event, dict) and event.get("type") in EVENT_LABEL:
                records.append(event)
    if not run.is_complete():
        records.extend(e for e in run.event_log if e.get("type") in EVENT_LABEL)
    return records


def codex_entries():
    """E-12: one row per event type, in EVENT_LABEL order."""
    records = lifetime_event_records()
    in_progress = {}
    if not run.is_complete():
        for event in run.event_log:
            in_progress[event["type"]] = in_progress.get(event["type"], 0) + 1
    rows = []
    for event_type in EVENT_LABEL:
        mine = [e for e in records if e["type"] == event_type]
        faced = max(
            len(mine),
            int(legacy_event_counts.get(event_type, 0)) + in_progress.get(event_type, 0),
        )
        if faced == 0 and event_type in legacy_events:
            faced = 1
        row = {
            "type": event_type,
            "label": EVENT_LABEL[event_type],
            "icon": EVENT_ICON[event_type],
            "category": EVENT_CATEGORY[event_type],
            "faced": faced,
            "logged": len(mine),
            "avg_damage": None,
            "best_mitigation": None,
            "lowest_damage": None,
            "worst_damage": None,
            "flawless": 0,
            "example": REAL_WORLD_EXAMPLES.get(event_type) if faced else None,
        }
        if mine:
            damages = [e["damage"] for e in mine]
            row["avg_damage"] = sum(damages) / len(damages)
            row["lowest_damage"] = min(damages)
            row["worst_damage"] = max(damages)
            row["best_mitigation"] = max(entry_mitigation(e) or 0.0 for e in mine)
            row["flawless"] = flawless_count(mine)
        rows.append(row)
    return rows


def codex_completion():
    rows = codex_entries()
    return sum(1 for row in rows if row["faced"] > 0), len(rows)


def codex_summary_text():
    done, total = codex_completion()
    if done >= total:
        return f"Codex complete: all {total} kinds of shock recorded."
    return f"{done} of {total} kinds of shock recorded. Face each kind to fill its page and unlock its real-world note."


def event_source_hint(event_type):
    """FY-3: where an event type can be met, when it is not in the Classic
    schedule -- so the Codex can say how to fill a page that the default
    run never fills. Empty for a type the Classic mix already contains."""
    if event_type in SCENARIOS[DEFAULT_SCENARIO]["schedule"]:
        return ""
    names = [data["label"] for data in SCENARIOS.values() if event_type in data["schedule"]]
    if not names:
        return ""
    return " It only arrives in the " + " or ".join(names) + " scenario" + ("s" if len(names) > 1 else "") + ", chosen before a run's first event."


def codex_stats_text(row):
    if row["faced"] == 0:
        return f"Not faced yet. Weather a {row['label']} to record it and unlock its real-world note.{event_source_hint(row['type'])}"
    if row["avg_damage"] is None:
        return f"Faced x{row['faced']}. Damage details are recorded for runs completed since the run log began."
    flawless = f" · Flawless Defense x{row['flawless']}" if row["flawless"] else ""
    return (
        f"Faced x{row['faced']} · average damage {row['avg_damage']:.0f} · "
        f"lowest {row['lowest_damage']:.0f}, worst {row['worst_damage']:.0f} · "
        f"best mitigation {row['best_mitigation'] * 100:.0f}%{flawless}"
    )


codex_open = False


def on_toggle_codex(event=None):
    global codex_open
    codex_open = not codex_open
    render_codex_panel()


def render_codex_panel():
    toggle = document.getElementById("codex-toggle-button")
    panel = document.getElementById("codex-panel")
    done, total = codex_completion()
    toggle.innerText = "Hide Disaster Codex" if codex_open else f"📖 Disaster Codex ({done}/{total})"
    panel.hidden = not codex_open
    if not codex_open:
        return
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "codex-heading"
    heading.innerText = "Disaster Codex"
    panel.appendChild(heading)
    summary = document.createElement("p")
    summary.className = "comparison-message codex-summary"
    summary.innerText = codex_summary_text()
    panel.appendChild(summary)
    for row in codex_entries():
        card = document.createElement("div")
        card.className = "codex-card" + ("" if row["faced"] else " codex-card--locked")
        title = document.createElement("p")
        title.className = f"codex-title event-category--{row['category']}"
        title.innerText = f"{row['icon']} {row['label']}" + (" ✓" if row["faced"] else " 🔒")
        card.appendChild(title)
        stats = document.createElement("p")
        stats.className = "codex-stats"
        stats.innerText = codex_stats_text(row)
        card.appendChild(stats)
        example = row["example"]
        if example:
            note = document.createElement("p")
            note.className = "codex-note"
            note.innerText = f"In the real world: {example['title']}. {example['text']}"
            card.appendChild(note)
            link = document.createElement("a")
            link.className = "real-world-source"
            link.href = example["url"]
            link.target = "_blank"
            link.rel = "noopener noreferrer"
            link.innerText = f"Source: {example['source']} (read {example.get('read', REAL_WORLD_READ_DATE)})"
            card.appendChild(link)
        panel.appendChild(card)


# ---- E-1: lifetime statistics, from run_log_history -----------------------
STAT_BANDS = (("0-1 skills", 0, 1), ("2-3 skills", 2, 3), ("4+ skills", 4, 999))
STATS_KP_ROWS = 15


def lifetime_stats():
    logs = [entry for entry in run_log_history if isinstance(entry, dict)]
    category_damage = {c: 0.0 for c in ("weather", "non-weather", "social", "health")}
    per_type = {}
    for entry in logs:
        for event in entry.get("event_log", []) or []:
            if not isinstance(event, dict) or event.get("type") not in EVENT_LABEL:
                continue
            event_type = event["type"]
            category_damage[EVENT_CATEGORY[event_type]] += event.get("damage", 0.0)
            per_type.setdefault(event_type, []).append(event)
    matchups = []
    for event_type, events in per_type.items():
        mitigations = [entry_mitigation(e) or 0.0 for e in events]
        matchups.append(
            {
                "type": event_type,
                "count": len(events),
                "avg_mitigation": sum(mitigations) / len(mitigations),
                "avg_damage": sum(e["damage"] for e in events) / len(events),
            }
        )
    matchups.sort(key=lambda m: (-m["avg_mitigation"], m["type"]))
    kp_rows = []
    running = 0
    for entry in logs:
        earned = int(entry.get("knowledge_earned", 0) or 0)
        running += earned
        kp_rows.append({"run_number": entry.get("run_number"), "earned": earned, "total": running})
    bands = []
    for label, low, high in STAT_BANDS:
        scores = [
            entry.get("score", 0.0)
            for entry in logs
            if isinstance(entry.get("skill_strength"), int) and low <= entry["skill_strength"] <= high
        ]
        bands.append({"label": label, "runs": len(scores), "avg_score": (sum(scores) / len(scores)) if scores else None})
    return {
        "runs": len(logs),
        "category_damage": category_damage,
        "matchups": matchups,
        "kp_rows": kp_rows,
        "bands": bands,
        "flawless": sum(
            flawless_count([ev for ev in (e.get("event_log", []) or []) if isinstance(ev, dict)]) for e in logs
        ),
    }


stats_open = False


def on_toggle_stats(event=None):
    global stats_open
    stats_open = not stats_open
    render_stats_panel()


def _stat_row(label, fraction, value_text):
    row = document.createElement("div")
    row.className = "stat-row"
    label_el = document.createElement("span")
    label_el.className = "stat-label"
    label_el.innerText = label
    row.appendChild(label_el)
    track = document.createElement("span")
    track.className = "stat-bar"
    track.setAttribute("aria-hidden", "true")
    fill = document.createElement("span")
    fill.className = "stat-bar-fill"
    fill.style.width = f"{max(0.0, min(1.0, fraction)) * 100:.0f}%"
    track.appendChild(fill)
    row.appendChild(track)
    value_el = document.createElement("span")
    value_el.className = "stat-value"
    value_el.innerText = value_text
    row.appendChild(value_el)
    return row


def _stat_heading(panel, text):
    heading = document.createElement("h3")
    heading.className = "stat-heading"
    heading.innerText = text
    panel.appendChild(heading)


def render_stats_panel():
    toggle = document.getElementById("stats-toggle-button")
    panel = document.getElementById("stats-panel")
    toggle.innerText = "Hide Lifetime Stats" if stats_open else "📊 Lifetime Stats"
    panel.hidden = not stats_open
    if not stats_open:
        return
    stats = lifetime_stats()
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "stats-heading"
    heading.innerText = "Lifetime Stats"
    panel.appendChild(heading)
    if not stats["runs"]:
        empty = document.createElement("p")
        empty.innerText = "No completed runs with a log yet. Finish a run and this page fills in."
        panel.appendChild(empty)
        return
    intro = document.createElement("p")
    intro.className = "comparison-message"
    intro.innerText = (
        f"Built from {stats['runs']} completed run{'s' if stats['runs'] != 1 else ''}. "
        "Every bar has its numbers written beside it."
    )
    panel.appendChild(intro)

    _stat_heading(panel, "Damage taken by category")
    total = sum(stats["category_damage"].values()) or 1.0
    for category, amount in stats["category_damage"].items():
        if category == "health" and amount <= 0:
            continue  # FY-3: the health category only exists in the Heat season scenario
        panel.appendChild(
            _stat_row(f"{CATEGORY_ICON[category]} {category.capitalize()}", amount / total,
                      f"{amount:.0f} damage ({amount / total * 100:.0f}%)")
        )

    _stat_heading(panel, "Average mitigation by event type")
    for item in stats["matchups"]:
        panel.appendChild(
            _stat_row(f"{EVENT_ICON[item['type']]} {EVENT_LABEL[item['type']]}", item["avg_mitigation"],
                      f"{item['avg_mitigation'] * 100:.0f}% prevented (avg {item['avg_damage']:.0f} damage, {item['count']} faced)")
        )
    if len(stats["matchups"]) >= 2:
        best, worst = stats["matchups"][0], stats["matchups"][-1]
        line = document.createElement("p")
        line.className = "stat-matchup"
        if best["avg_mitigation"] - worst["avg_mitigation"] < 0.005:
            line.innerText = "Every matchup is level so far: the same share of damage prevented against every kind of shock."
        else:
            line.innerText = (
                f"Best matchup: {EVENT_LABEL[best['type']]} ({best['avg_mitigation'] * 100:.0f}% prevented). "
                f"Worst matchup: {EVENT_LABEL[worst['type']]} ({worst['avg_mitigation'] * 100:.0f}% prevented)."
            )
        panel.appendChild(line)

    _stat_heading(panel, "Knowledge points over time")
    rows = stats["kp_rows"][-STATS_KP_ROWS:]
    most = max([r["earned"] for r in rows] + [1])
    for item in rows:
        panel.appendChild(
            _stat_row(f"Run {item['run_number']}", item["earned"] / most, f"+{item['earned']} (total {item['total']})")
        )
    if len(stats["kp_rows"]) > len(rows):
        note = document.createElement("p")
        note.className = "comparison-message"
        note.innerText = f"Showing the last {len(rows)} of {len(stats['kp_rows'])} runs."
        panel.appendChild(note)

    _stat_heading(panel, "Average score by skill strength")
    scored = [b["avg_score"] for b in stats["bands"] if b["avg_score"] is not None]
    top = max(scored + [1.0])
    for band in stats["bands"]:
        if band["avg_score"] is None:
            panel.appendChild(_stat_row(band["label"], 0.0, "no runs yet"))
        else:
            panel.appendChild(
                _stat_row(band["label"], band["avg_score"] / top,
                          f"{band['avg_score']:.0f} average over {band['runs']} run{'s' if band['runs'] != 1 else ''}")
            )
    note = document.createElement("p")
    note.className = "comparison-message"
    note.innerText = "Skill strength is recorded for runs completed from this update on; older runs are not in these bands."
    panel.appendChild(note)

    flawless = document.createElement("p")
    flawless.className = "stat-matchup"
    flawless.innerText = f"Flawless Defenses so far: {stats['flawless']}."
    panel.appendChild(flawless)


# ---- GE-15 hint, GE-13 popup, E-5 announcements -------------------------
def flawless_threshold(event_type):
    return EVENT_BASE_DAMAGE[event_type] * FLAWLESS_DAMAGE_FRACTION


def flawless_hint_text(run_state):
    """GE-15: always tells the player what a Flawless Defense needs for the
    coming event, and whether the current build is on track."""
    if run_state.is_complete():
        return ""
    event_type = run_state.next_event_type()
    limit = flawless_threshold(event_type)
    damage, _severity = expected_next_event_damage(run_state)
    status = "on track" if damage <= limit + 1e-9 else f"expected {damage:.0f}"
    return (
        f"Flawless Defense (+{FLAWLESS_BONUS_KNOWLEDGE} knowledge): hold {EVENT_LABEL[event_type]} damage to "
        f"{limit:.0f} or less ({status})."
    )


def event_announcement(entry):
    prevented = entry_prevented(entry)
    text = (
        f"{EVENT_LABEL[entry['type']]} hit, {entry['damage']:.0f} damage, {prevented:.0f} prevented."
    )
    if entry_is_flawless(entry):
        text += " Flawless Defense."
    return text


def _shared_announce(text):
    """B-7: speak through shared/announcer.js when the page has it (returns True); otherwise the game's own
    live region is used. Never both, so a screen reader does not read a message twice."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    shared = getattr(window, "NoyvjAnnounce", None)
    if shared is None:
        return False
    try:
        shared.say(str(text))
    except Exception:  # noqa: BLE001 -- an announcement must never break the game
        return False
    return True


def announce(text):
    element = document.getElementById("event-announcer")
    if text and _shared_announce(text):
        element.innerText = ""
        return
    element.innerText = text


def render_damage_popup():
    popup = document.getElementById("damage-prevented-popup")
    streak_el = document.getElementById("damage-streak-display")
    if not run.event_log:
        popup.hidden = True
        streak_el.hidden = True
        popup.innerText = ""
        streak_el.innerText = ""
        return
    last = run.event_log[-1]
    prevented = entry_prevented(last)
    popup.hidden = False
    if prevented >= 1:
        popup.innerText = f"-{prevented:.0f} damage prevented!"
    else:
        popup.innerText = "No damage prevented. More resilience softens the next hit."
    popup.dataset.prevented = str(int(round(prevented)))
    popup.dataset.eventKey = f"{run.run_number}-{len(run.event_log)}"
    parts = []
    streak = held_streak(run.event_log)
    if streak >= 2:
        parts.append(f"🔥 Held {streak} events in a row")
    if entry_is_flawless(last):
        parts.append(f"✨ Flawless Defense: +{FLAWLESS_BONUS_KNOWLEDGE} knowledge at the end of the run")
    streak_el.innerText = " · ".join(parts)
    streak_el.hidden = not parts


# ---- E-23: knowledge itemisation ---------------------------------------
def knowledge_breakdown_lines(run_state):
    info = run_state.knowledge_breakdown()
    lines = [f"Resources left {info['resources']:.0f} ÷ 20 = {info['raw']} knowledge"]
    if info.get("schedule_factor", 1.0) < 1.0:
        lines.append(
            f"Custom schedule: {info['schedule_factor'] * 100:.0f}% of the Classic mix's damage, "
            "so the base knowledge is scaled to match"
        )
    if info["floor_applied"]:
        lines.append("Minimum of 1 applied: no run ever earns nothing")
    if info["flawless"]:
        lines.append(
            f"Flawless Defense x{info['flawless']}: +{info['flawless_bonus']} knowledge"
        )
    lines.append(f"Total: {info['total']} knowledge point{'s' if info['total'] != 1 else ''}")
    return lines


def knowledge_preview_detail(run_state):
    info = run_state.knowledge_breakdown()
    detail = f"{info['base']} from {info['resources']:.0f} resources"
    if info["flawless"]:
        detail += f", +{info['flawless_bonus']} Flawless Defense"
    return f" ({detail})"


# ---- E-24: copy run summary --------------------------------------------
def run_summary_text(run_state=None):
    run_state = run_state or run
    name = meta["settlement_name"] or "My settlement"
    scenario = SCENARIOS[run_state.scenario]["label"]
    done = run_state.is_complete()
    lines = [
        f"Aftermath: {name}, run {run_state.run_number} ({scenario}{', extended' if run_state.extended else ''})"
        + ("" if done else " - in progress"),
        f"{'Score' if done else 'Resources so far'}: {run_state.run_score():.0f}"
        + (f" ({adjusted_text(run_state.run_score(), run_state.event_log)})" if done else "")
        + (f" | Knowledge earned: {run_state.knowledge_points_earned()}" if done else ""),
        f"Resilience {run_state.resilience_capacity}, growth {run_state.growth_capacity}, "
        f"damage taken {run_state.damage_taken:.0f}",
    ]
    for index, entry in enumerate(run_state.event_log, start=1):
        extra = " (flawless)" if entry_is_flawless(entry) else ""
        lines.append(
            f"{index}. {EVENT_LABEL[entry['type']]}: {entry['damage']:.0f} damage, "
            f"{entry_prevented(entry):.0f} prevented, {severity_label(entry['severity'])}{extra}"
        )
    return "\n".join(lines)


def copy_result_fields(run_state=None):
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Aftermath, 340 resources left, run 3 (Coastal), 5 events, ...". Read
    by the page's own inline script through pyodide.globals when the shared
    Copy result button is pressed, so it always matches the run right now."""
    run_state = run_state or run
    events = len(run_state.event_log)
    flawless = flawless_count(run_state.event_log)
    stats = [
        f"run {run_state.run_number} ({SCENARIOS[run_state.scenario]['label']})" + ("" if run_state.is_complete() else ", in progress"),
        {"n": events, "one": "event weathered", "many": "events weathered"},
        f"{run_state.damage_taken:.0f} damage taken",
    ]
    if flawless:
        stats.append({"n": flawless, "one": "flawless defense", "many": "flawless defenses"})
    return {
        "game": "Aftermath",
        "score": round(run_state.run_score()),
        "unit": "resources left" if run_state.is_complete() else "resources so far",
        "stats": stats,
    }


def _copy_to_clipboard(text):
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    navigator = getattr(_js, "navigator", None)
    clipboard = getattr(navigator, "clipboard", None) if navigator is not None else None
    if clipboard is None:
        return False
    try:
        clipboard.writeText(text)
        return True
    except Exception:
        return False


def on_copy_run_summary(event=None):
    text = run_summary_text()
    status = document.getElementById("copy-run-summary-status")
    area = document.getElementById("copy-run-summary-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        status.innerText = "Copied the run summary to the clipboard."
    else:
        area.hidden = False
        area.value = text
        status.innerText = "Could not copy automatically. Select the text below and copy it yourself."


# ---- E-27: live tab title ----------------------------------------------
def tab_title(run_state=None):
    run_state = run_state or run
    if run_state.is_complete():
        return f"Aftermath - Run {run_state.run_number} complete, score {run_state.run_score():.0f}"
    return (
        f"Aftermath - Run {run_state.run_number}, event {run_state.event_index + 1} of {len(run_state.schedule)} "
        f"({EVENT_LABEL[run_state.next_event_type()]} next)"
    )


def update_tab_title():
    try:
        document.title = tab_title()
    except Exception:
        pass


# ---- E-29: what a locked skill would help against ---------------------------
# Extra mitigation a skill adds, as {skill_id: (category or None for every event, amount)}.
SKILL_MITIGATION_EXTRA = {
    "early_warning": (None, 0.10),
    "mutual_aid_network": (None, 0.05),
    "civic_preparedness": ("social", 0.35),
    "climate_hardening": ("weather", 0.20),
}


def skill_helps_against(skill_id, run_state=None):
    """For a mitigation skill: ({event label: count}, total damage it would save)
    over the events still to come in this run, from the exact deterministic
    severities, so the line matches what would really happen. None for a skill
    that changes the starting build instead (it applies from the next run)."""
    rule = SKILL_MITIGATION_EXTRA.get(skill_id)
    if rule is None:
        return None
    run_state = run_state or run
    category, amount = rule
    counts = {}
    saved = 0.0
    for index in range(run_state.event_index, len(run_state.schedule)):
        event_type = run_state.schedule[index]
        if category is not None and EVENT_CATEGORY[event_type] != category:
            continue
        current = run_state.mitigation_for(event_type)
        gain = min(MAX_MITIGATION, current + amount) - current
        severity = run_state.severity_at(index)
        saved += EVENT_BASE_DAMAGE[event_type] * severity * gain
        counts[EVENT_LABEL[event_type]] = counts.get(EVENT_LABEL[event_type], 0) + 1
    return counts, saved


def skill_helps_text(skill_id, run_state=None):
    """The 'Helps against' line shown under a locked skill. Empty once unlocked."""
    if skill_id in skill_tree.unlocked:
        return ""
    run_state = run_state or run
    if run_state.normalised:
        return "Skills are switched off in a challenge run."
    result = skill_helps_against(skill_id, run_state)
    if result is None:
        if skill_id == "reinforced_infrastructure":
            return "Helps from your next run's first event: +2 resilience is +10% mitigation against every kind of event."
        if skill_id == "community_reserves":
            return "Helps from your next run's first event: 50 more resources to absorb whatever comes first."
        if skill_id == "adaptive_growth":
            events = len(run_state.schedule)
            return f"Helps every event of your next run: +{GROWTH_INCOME_PER_UNIT} resources per event, about +{GROWTH_INCOME_PER_UNIT * events} over {events} events."
        return ""
    counts, saved = result
    if not counts:
        kind = SKILL_MITIGATION_EXTRA[skill_id][0]
        if run_state.is_complete():
            return f"Helps against: {kind or 'every'} events in your next run."
        return f"Helps against: nothing left in this run's schedule (it softens {kind} events, which return in your next run)."
    names = ", ".join(f"{label} \u00d7{count}" if count > 1 else label for label, count in counts.items())
    return f"Helps against: {names}. About {saved:.0f} less damage over the rest of this run at your current build."


# ---- E-18: damage waterfall -----------------------------------------------
def waterfall_lines(breakdown):
    """The text equivalent of the waterfall, one step per line."""
    lines = [f"Base damage: {breakdown['base']:.0f}"]
    change = breakdown["unmitigated"] - breakdown["base"]
    sign = "+" if change >= 0 else "\u2212"
    lines.append(
        f"Severity {breakdown['severity']:.2f}\u00d7 ({severity_label(breakdown['severity'])}): "
        f"{sign}{abs(change):.0f}, so {breakdown['unmitigated']:.0f} before any protection"
    )
    for source in breakdown["sources"]:
        lines.append(f"{source['label']}: \u2212{source['damage']:.0f} ({source['fraction'] * 100:.0f}% of the damage)")
    if breakdown["cap_added_back"] > 0.5:
        lines.append(
            f"Mitigation cap ({MAX_MITIGATION * 100:.0f}%): +{breakdown['cap_added_back']:.0f} damage the protection could not stop"
        )
    lines.append(f"Damage taken: {breakdown['final']:.0f}")
    return lines


def waterfall_segments(breakdown):
    """(label, share of the unmitigated damage 0..1, kind) for the stacked
    bar: what each source really prevented (scaled down proportionally when
    the cap bit) and what got through."""
    unmitigated = breakdown["unmitigated"] or 1.0
    raw = sum(s["fraction"] for s in breakdown["sources"])
    scale = (breakdown["mitigation"] / raw) if raw > 0 else 0.0
    segments = [(s["label"], s["fraction"] * scale, "prevented") for s in breakdown["sources"]]
    segments.append(("Damage taken", breakdown["final"] / unmitigated, "taken"))
    return segments


def render_damage_waterfall():
    wrapper = document.getElementById("damage-waterfall")
    body = document.getElementById("damage-waterfall-body")
    if wrapper is None or body is None:
        return
    breakdown = run.last_breakdown
    if not run.event_log or breakdown is None:
        wrapper.hidden = True
        body.innerHTML = ""
        return
    wrapper.hidden = False
    body.innerHTML = ""
    bar = document.createElement("div")
    bar.className = "waterfall-bar"
    bar.setAttribute("role", "img")
    bar.setAttribute("aria-label", "; ".join(waterfall_lines(breakdown)))
    for label, share, kind in waterfall_segments(breakdown):
        if share <= 0.0005:
            continue
        seg = document.createElement("div")
        seg.className = f"waterfall-seg waterfall-seg--{kind}"
        seg.style.width = f"{share * 100:.1f}%"
        seg.title = f"{label}: {share * 100:.0f}%"
        bar.appendChild(seg)
    body.appendChild(bar)
    for text in waterfall_lines(breakdown):
        line = document.createElement("p")
        line.className = "waterfall-line"
        line.innerText = text
        body.appendChild(line)


# ---- GE-21: closing line (epitaph) on the run summary --------------------------
# One short line per finished run, picked from a bank keyed to how the run went. The pick is
# deterministic (run number, so it never flickers between renders and replaying the same run reads
# the same). Lines for a hard run stay gentle on purpose; the dry jokes are kept for runs that went
# well. A Settings checkbox hides it (key written by settings.js).
HIDE_EPITAPH_STORAGE_KEY = "aftermath-hide-epitaph"
EPITAPHS = {
    "ruin": [
        "The settlement is still standing. It just needs a long sit-down.",
        "Every shock left a lesson, and the notes are already in the tree.",
        "A rough run. The people remember what worked, and so does your skill tree.",
        "Tomorrow's plan starts from today's scars, and that is how plans improve.",
        "Nothing is wasted: this run's hard hits are next run's early warnings.",
        "Rebuilding is also a result. Take what it taught you.",
    ],
    "flawless": [
        "The levee held. The mayor, as ever, took the credit.",
        "At least one disaster arrived and found nobody home to hurt.",
        "A shock walked in, read the sea wall, and left.",
        "Perfectly defended, and not one person had to be heroic about it.",
        "The best disaster plan is the one nobody notices until afterwards.",
        "Insurance adjusters were seen weeping with happiness.",
    ],
    "rich": [
        "Weathered it all and still finished with money in the bank.",
        "The settlement ended the year richer than it started. Suspicious, but welcome.",
        "Growth and good luck? No, growth and good planning.",
        "The treasurer would like it noted that this was never in doubt.",
        "Disasters came, the budget stayed standing.",
        "A surplus after seven shocks. The history books will need a bigger margin.",
    ],
    "resilience": [
        "Built to last, and it did.",
        "The walls were thick, the people were prepared, and the weather had to take notes.",
        "Everything was reinforced, including the committee meetings.",
        "A settlement that spent early and slept well.",
        "Concrete, drills and good habits: boring on purpose, and it worked.",
        "When the storm came, the most dramatic thing was the forecast.",
    ],
    "growth": [
        "Fast growth, thin margins, and it still came through.",
        "The economy kept humming through every shock.",
        "Income first, armour later, and the bet paid off this time.",
        "A busy settlement: too busy to be flattened.",
        "The market stalls reopened before the water had finished draining.",
        "Prosperity is also a kind of preparedness.",
    ],
    "steady": [
        "Seven shocks, one settlement, still here.",
        "Nothing glamorous, nothing lost. That is what resilience looks like.",
        "A steady run: the kind that does not make the news, which is the point.",
        "The shocks came and went, and so did the worry.",
        "A solid year. Next year's weather will not care, and neither will you.",
        "Survival, with room for improvement.",
    ],
}
SCENARIO_EPITAPHS = {
    "heat_season": "The summer is over. The shade, the water and the neighbours who checked in all counted.",
    "coastal": "The tide went out again and the harbour was still there.",
    "urban": "The city kept its lights on, its trains running and its arguments civil, mostly.",
}


def epitaph_kind(run_state):
    """Which bucket of EPITAPHS fits a finished run, checked in this order."""
    if run_state.resources <= 0 or run_state.run_score() <= VERY_BAD_RUN_SCORE:
        return "ruin"
    if flawless_count(run_state.event_log) >= 1:
        return "flawless"
    if run_state.resources > run_state.starting_resources:
        return "rich"
    if run_state.resilience_capacity >= 3 and run_state.resilience_capacity > run_state.growth_capacity:
        return "resilience"
    if run_state.growth_capacity >= 3 and run_state.growth_capacity > run_state.resilience_capacity:
        return "growth"
    return "steady"


def epitaph_text(run_state):
    """The closing line for a finished run: a scenario line on every third run of that scenario
    (never over a ruinous run), otherwise from the outcome bucket."""
    kind = epitaph_kind(run_state)
    if kind != "ruin" and run_state.scenario in SCENARIO_EPITAPHS and run_state.run_number % 3 == 0:
        return SCENARIO_EPITAPHS[run_state.scenario]
    bank = EPITAPHS[kind]
    return bank[(run_state.run_number * 5 + len(run_state.event_log)) % len(bank)]


def epitaph_hidden():
    return localStorage.getItem(HIDE_EPITAPH_STORAGE_KEY) == "true"


# ---- E-17: schedule strip -------------------------------------------------
def schedule_strip_entries(run_state):
    """One entry per event in the run's schedule: what it is, whether it is
    done / next / upcoming, and the numbers to show. Upcoming damage is exact
    for this run number (severity is deterministic) at the CURRENT build, so
    it moves as the player invests."""
    entries = []
    for index, event_type in enumerate(run_state.schedule):
        category = EVENT_CATEGORY[event_type]
        entry = {
            "index": index,
            "number": index + 1,
            "type": event_type,
            "label": EVENT_LABEL[event_type],
            "icon": EVENT_ICON[event_type],
            "category": category,
            "category_bonus": run_state.category_bonus(event_type),
        }
        if index < run_state.event_index and index < len(run_state.event_log):
            logged = run_state.event_log[index]
            entry.update(
                state="done",
                damage=logged["damage"],
                severity=logged.get("severity", 1.0),
                mitigation=entry_mitigation(logged),
            )
        else:
            severity = run_state.severity_at(index)
            mitigation = run_state.mitigation_for(event_type)
            entry.update(
                state="next" if index == run_state.event_index else "upcoming",
                damage=EVENT_BASE_DAMAGE[event_type] * severity * (1 - mitigation),
                severity=severity,
                mitigation=mitigation,
            )
        entries.append(entry)
    return entries


def schedule_entry_text(entry):
    """The plain-text detail for one strip entry (hover, focus and screen readers)."""
    head = f"Event {entry['number']}: {entry['label']} ({entry['category']} shock)."
    severity = f"{entry['severity']:.2f}\u00d7 severity, {severity_label(entry['severity'])}"
    if entry["state"] == "done":
        mitigation = entry["mitigation"]
        held = f", {mitigation * 100:.0f}% prevented" if mitigation is not None else ""
        return f"{head} Faced: {entry['damage']:.0f} damage ({severity}{held})."
    bonus = entry["category_bonus"]
    bonus_text = f"a {bonus * 100:.0f}% category bonus" if bonus else "no category bonus"
    when = "Next" if entry["state"] == "next" else "Upcoming"
    return (
        f"{head} {when}: about {entry['damage']:.0f} damage at your current build "
        f"({severity}; {entry['mitigation'] * 100:.0f}% mitigation, {bonus_text})."
    )


def render_schedule_strip():
    strip = document.getElementById("schedule-strip")
    if strip is None:
        return  # a cached older page without the strip (service worker serves stale HTML once)
    strip.innerHTML = ""
    entries = schedule_strip_entries(run)
    default_text = ""
    for entry in entries:
        text = schedule_entry_text(entry)
        if entry["state"] == "next":
            default_text = text
        mark = {"done": "\u2713 ", "next": "\u25b6 ", "upcoming": ""}[entry["state"]]
        chip = document.createElement("li")
        chip.className = f"schedule-chip schedule-chip--{entry['state']} event-category--{entry['category']}"
        chip.innerText = f"{mark}{entry['number']} {entry['icon']} {entry['label']}"
        chip.title = text
        chip.setAttribute("tabindex", "0")
        chip.setAttribute("aria-label", text)
        chip.setAttribute("data-detail", text)
        strip.appendChild(chip)
    if not default_text:
        default_text = f"Run complete: all {len(entries)} events faced."
    detail = document.getElementById("schedule-detail")
    detail.innerText = default_text
    detail.setAttribute("data-default", default_text)


# ---------------------------------------------------------------------------
# Round-3 batch 2 (2026-10-10): E-19 tree search/filters, E-25 allocation presets, E-30 save
# health badge, E-3 purchase route planner, E-13 schedule builder, E-4 shareable run codes and the
# last E-5 pieces (plain-text schedule). Each section says what it owns.
# ---------------------------------------------------------------------------
def _el(element_id):
    """getElementById that returns None for an id a cached older page does not have (the real DOM
    returns null; the test fake raises KeyError)."""
    try:
        return document.getElementById(element_id)
    except KeyError:
        return None


def _focus(element):
    try:
        element.focus()
    except Exception:
        pass


# ---- E-19: skill tree search and filter chips ------------------------------
SKILL_GROUP = {
    "reinforced_infrastructure": "starting",
    "community_reserves": "starting",
    "adaptive_growth": "starting",
    "early_warning": "mitigation",
    "mutual_aid_network": "mitigation",
    "climate_hardening": "weather",
    "civic_preparedness": "social",
}
SKILL_GROUP_LABEL = {"weather": "Weather", "social": "Social", "mitigation": "All events", "starting": "Starting build"}
SKILL_STATUS_FILTERS = (("all", "All"), ("affordable", "Affordable"), ("pinned", "Pinned"), ("owned", "Owned"))
SKILL_GROUP_FILTERS = (("any", "Any type"),) + tuple(SKILL_GROUP_LABEL.items())
skill_search_text = ""
skill_filter_status = "all"
skill_filter_group = "any"


def skill_matches(skill_id, query=None, status=None, group=None):
    """True when the skill passes the search words (every word must appear in its name, effect,
    real-world note or type), the status chip (Affordable = can be unlocked right now, Pinned,
    Owned) and the type chip."""
    query = skill_search_text if query is None else query
    status = skill_filter_status if status is None else status
    group = skill_filter_group if group is None else group
    skill = SKILLS[skill_id]
    owned = skill_id in skill_tree.unlocked
    if status == "owned" and not owned:
        return False
    if status == "affordable" and not skill_tree.can_unlock(skill_id):
        return False
    if status == "pinned" and not (skill_id in meta["pinned_skills"] and not owned):
        return False
    if group != "any" and SKILL_GROUP.get(skill_id) != group:
        return False
    words = str(query or "").casefold().split()
    if words:
        haystack = " ".join(
            [skill["label"], skill["description"], skill["real_practice"], SKILL_GROUP_LABEL.get(SKILL_GROUP.get(skill_id), "")]
        ).casefold()
        if not all(word in haystack for word in words):
            return False
    return True


def visible_skill_ids():
    return [skill_id for skill_id in SKILLS if skill_matches(skill_id)]


def skill_filters_active():
    return bool(skill_search_text.strip()) or skill_filter_status != "all" or skill_filter_group != "any"


def skill_filter_summary():
    shown = len(visible_skill_ids())
    if shown == 0:
        return "No skills match. Clear the search or pick All."
    if not skill_filters_active():
        return f"Showing all {len(SKILLS)} skills."
    return f"Showing {shown} of {len(SKILLS)} skills."


def set_skill_filter(kind, value):
    global skill_filter_status, skill_filter_group
    if kind == "status" and value in dict(SKILL_STATUS_FILTERS):
        skill_filter_status = value
    elif kind == "group" and value in dict(SKILL_GROUP_FILTERS):
        skill_filter_group = value
    else:
        return False
    return True


def clear_skill_filters():
    global skill_search_text, skill_filter_status, skill_filter_group
    skill_search_text, skill_filter_status, skill_filter_group = "", "all", "any"
    search = _el("skill-search-input")
    if search is not None:
        search.value = ""


def on_skill_search(event=None):
    global skill_search_text
    search = _el("skill-search-input")
    skill_search_text = str(search.value or "") if search is not None else ""
    render()


def _make_skill_filter_handler(kind, value):
    def handler(event=None):
        set_skill_filter(kind, value)
        render()
    return handler


def on_skill_filter_clear(event=None):
    clear_skill_filters()
    render()


def build_skill_filter_chips():
    """Builds the chip buttons once (so keyboard focus survives every render)."""
    holder = _el("skill-filter-chips")
    if holder is None:
        return
    holder.innerHTML = ""
    for kind, options in (("status", SKILL_STATUS_FILTERS), ("group", SKILL_GROUP_FILTERS)):
        group_el = document.createElement("div")
        group_el.className = "skill-filter-group"
        group_el.setAttribute("role", "group")
        group_el.setAttribute("aria-label", "Show by status" if kind == "status" else "Show by type")
        for value, label in options:
            chip = document.createElement("button")
            chip.className = "secondary skill-filter-chip"
            chip.setAttribute("type", "button")
            chip.setAttribute("data-filter-kind", kind)
            chip.setAttribute("data-filter-value", value)
            chip.setAttribute("aria-pressed", "false")
            chip.innerText = label
            chip.addEventListener("click", create_proxy(_make_skill_filter_handler(kind, value)))
            group_el.appendChild(chip)
        holder.appendChild(group_el)


def render_skill_filters():
    holder = _el("skill-filter-chips")
    if holder is not None:
        for group_el in holder.children:
            for chip in group_el.children:
                kind = chip.getAttribute("data-filter-kind")
                value = chip.getAttribute("data-filter-value")
                active = (skill_filter_status if kind == "status" else skill_filter_group) == value
                chip.setAttribute("aria-pressed", "true" if active else "false")
                if active:
                    chip.classList.add("selected")
                else:
                    chip.classList.remove("selected")
    visible = set(visible_skill_ids())
    for skill_id in SKILLS:
        row = _el(f"skill-{skill_id}-row")
        if row is not None:
            row.hidden = skill_id not in visible
    summary = _el("skill-filter-summary")
    if summary is not None:
        summary.innerText = skill_filter_summary()
    clear = _el("skill-filter-clear")
    if clear is not None:
        clear.hidden = not skill_filters_active()


# ---- E-25: named allocation presets -----------------------------------------
preset_selected = ""
preset_status_text = ""


def preset_text(preset):
    parts = []
    if preset["resilience"]:
        parts.append(f"{preset['resilience']} resilience")
    if preset["growth"]:
        parts.append(f"{preset['growth']} growth")
    return f"{preset['name']}: {', '.join(parts)}"


def _preset_named(name):
    key = _clean_name(name, PRESET_NAME_MAX).casefold()
    for preset in meta["presets"]:
        if preset["name"].casefold() == key:
            return preset
    return None


def save_preset(name, resilience, growth):
    """Adds or replaces (same name, any case) a preset. Returns (ok, message)."""
    name = _clean_name(name, PRESET_NAME_MAX)
    if not name:
        return False, "Give the preset a name."
    try:
        resilience, growth = int(resilience), int(growth)
    except (TypeError, ValueError):
        return False, "Units must be whole numbers."
    if _units(resilience) is None or _units(growth) is None:
        return False, f"Units must be between 0 and {PRESET_UNITS_MAX}."
    if resilience + growth < 1:
        return False, "Choose at least one unit of resilience or growth."
    existing = _preset_named(name)
    if existing is None and len(meta["presets"]) >= PRESET_MAX:
        return False, f"You can keep up to {PRESET_MAX} presets. Delete one first."
    entry = {"name": name, "resilience": resilience, "growth": growth}
    if existing is None:
        meta["presets"].append(entry)
    else:
        meta["presets"][meta["presets"].index(existing)] = entry
    save_meta()
    return True, f"{'Updated' if existing else 'Saved'} preset: {preset_text(entry)}."


def delete_preset(name):
    existing = _preset_named(name)
    if existing is None:
        return False
    meta["presets"].remove(existing)
    save_meta()
    return True


def apply_preset(name, run_state=None):
    """Buys a preset's units as ONE undoable click: resilience first (stopping at the 85% cap),
    then growth, each limited by the resources in hand. Returns (message, bought_resilience,
    bought_growth)."""
    run_state = run_state or run
    preset = _preset_named(name)
    if preset is None:
        return "That preset no longer exists.", 0, 0
    if run_state.is_complete():
        return "This run is over: start a new run to use a preset.", 0, 0
    bought_r, bought_g = run_state.invest_preset(preset["resilience"], preset["growth"])
    if bought_r == preset["resilience"] and bought_g == preset["growth"]:
        return f"Applied {preset['name']}: bought {bought_r} resilience, {bought_g} growth.", bought_r, bought_g
    if not bought_r and not bought_g:
        return f"{preset['name']}: nothing bought, not enough resources.", 0, 0
    reasons = []
    if bought_r < preset["resilience"]:
        reasons.append("resilience is at its 85% cap" if run_state.resilience_units_to_cap() == 0 and run_state.resources >= RESILIENCE_COST else "not enough resources")
    if bought_g < preset["growth"] and "not enough resources" not in reasons:
        reasons.append("not enough resources")
    return (
        f"Applied {preset['name']} in part: bought {bought_r} of {preset['resilience']} resilience and "
        f"{bought_g} of {preset['growth']} growth ({'; '.join(reasons)}).",
        bought_r,
        bought_g,
    )


def this_turn_allocation(run_state=None):
    """(resilience, growth) units bought since the last event: what 'Use this turn' copies."""
    run_state = run_state or run
    resilience = growth = 0
    for kind, units in run_state.allocation_history:
        if kind == "resilience":
            resilience += units
        elif kind == "growth":
            growth += units
        else:  # a preset click
            resilience += units[0]
            growth += units[1]
    return resilience, growth


def _int_or_zero(text):
    try:
        return int(str(text).strip() or 0)
    except ValueError:
        return -1


def on_preset_save(event=None):
    global preset_status_text, preset_selected
    name_el = _el("preset-name-input")
    ok, message = save_preset(
        name_el.value if name_el is not None else "",
        _int_or_zero(_el("preset-resilience-input").value),
        _int_or_zero(_el("preset-growth-input").value),
    )
    preset_status_text = message
    if ok:
        preset_selected = _clean_name(name_el.value, PRESET_NAME_MAX)
    render()
    announce(message)


def on_preset_from_turn(event=None):
    global preset_status_text
    resilience, growth = this_turn_allocation()
    _el("preset-resilience-input").value = str(resilience)
    _el("preset-growth-input").value = str(growth)
    preset_status_text = (
        f"Filled in {resilience} resilience, {growth} growth from this turn. Name it and press Save."
        if resilience or growth else "Nothing bought this turn yet: buy some units first, or type the numbers."
    )
    render()


def on_preset_apply(event=None):
    global preset_status_text
    select = _el("preset-select")
    name = select.value if select is not None else preset_selected
    message, _r, _g = apply_preset(name)
    preset_status_text = message
    render()
    announce(message)
    _check_new_achievements_for_toast()


def on_preset_select(event=None):
    global preset_selected
    select = _el("preset-select")
    if select is not None:
        preset_selected = select.value


def on_preset_list_event(event=None):
    global preset_status_text
    target = getattr(event, "target", None)
    if target is None:
        return
    action, name = target.getAttribute("data-action"), target.getAttribute("data-name")
    if not action or not name:
        return
    if action == "apply":
        message, _r, _g = apply_preset(name)
        preset_status_text = message
        announce(message)
        _check_new_achievements_for_toast()
    elif action == "delete" and delete_preset(name):
        preset_status_text = f"Deleted preset {name}."
        announce(preset_status_text)
    render()


def render_presets():
    global preset_selected
    presets = meta["presets"]
    if preset_selected and _preset_named(preset_selected) is None:
        preset_selected = ""
    if not preset_selected and presets:
        preset_selected = presets[0]["name"]
    row = _el("preset-apply-row")
    if row is not None:
        row.hidden = not presets or run.is_complete()
    select = _el("preset-select")
    if select is not None:
        select.innerHTML = ""
        for preset in presets:
            option = document.createElement("option")
            option.value = preset["name"]
            option.innerText = preset_text(preset)
            select.appendChild(option)
        select.value = preset_selected
    apply_button = _el("preset-apply-button")
    if apply_button is not None:
        apply_button.disabled = not presets or run.is_complete()
    listing = _el("preset-list")
    if listing is not None:
        listing.innerHTML = ""
        if not presets:
            empty = document.createElement("li")
            empty.innerText = "No presets yet. Buy some units, press Use this turn, name it and Save."
            listing.appendChild(empty)
        for preset in presets:
            item = document.createElement("li")
            item.className = "preset-item"
            label = document.createElement("span")
            label.className = "preset-item-label"
            label.innerText = preset_text(preset)
            item.appendChild(label)
            for action, text, extra in (("apply", "Apply", ""), ("delete", "Delete", " preset-delete")):
                button = document.createElement("button")
                button.className = "secondary preset-item-button" + extra
                button.setAttribute("type", "button")
                button.setAttribute("data-action", action)
                button.setAttribute("data-name", preset["name"])
                button.setAttribute("aria-label", f"{text} preset {preset['name']}")
                button.innerText = text
                button.disabled = action == "apply" and run.is_complete()
                item.appendChild(button)
            listing.appendChild(item)
    status = _el("preset-status")
    if status is not None:
        status.innerText = preset_status_text


# ---- E-30: save health badge --------------------------------------------------
save_health_announced = ""


def render_save_health():
    global save_health_announced
    badge = _el("save-health")
    if badge is None:
        return
    state, text = storage_health()
    badge.setAttribute("data-state", state)
    last = _storage_state["last_ok"]
    badge.setAttribute("data-saved-at", str(int(last * 1000)) if last is not None else "")
    text_el = _el("save-health-text")
    if text_el is not None:
        text_el.innerText = text
    export_button = _el("save-health-export-button")
    if export_button is not None:
        export_button.hidden = state not in ("failed", "unsaved")
    alert = _el("save-health-alert")
    if alert is not None and state != save_health_announced:
        # A polite live region, written only when the state changes, so the ticking age never talks.
        alert.innerText = text if state in ("failed", "unsaved") else ("Progress is saving again." if save_health_announced in ("failed", "unsaved") else "")
    save_health_announced = state


def on_save_health_export(event=None):
    """One click: builds the progress code, shows it selected in a box and tries the clipboard."""
    area = _el("save-health-code")
    status = _el("save-health-code-status")
    code = export_progress_code()
    if area is not None:
        area.hidden = False
        area.value = code
        _focus(area)
        try:
            area.select()
        except Exception:
            pass
    copied = _copy_to_clipboard(code)
    if status is not None:
        status.innerText = (
            "Copied your progress code. Paste it somewhere safe; Import Progress restores it."
            if copied else
            "Copy this code and keep it somewhere safe; Import Progress (Backup / Transfer) restores it."
        )


# ---- E-3: purchase route planner ----------------------------------------------
def purchase_route(pinned=None):
    """Ordered skill ids to buy for the pinned skills: each pinned skill (in pin order) preceded
    by any prerequisite not yet owned or already in the list, so the order always respects the
    tree. Owned skills are skipped."""
    pinned = list(meta["pinned_skills"]) if pinned is None else list(pinned)
    order = []

    def visit(skill_id):
        if skill_id not in SKILLS or skill_id in skill_tree.unlocked or skill_id in order:
            return
        for prereq in SKILLS[skill_id].get("prereqs", []):
            visit(prereq)
        order.append(skill_id)

    for skill_id in pinned:
        visit(skill_id)
    return order


def route_rows():
    """One row per step: the skill, its cost, the running total, how many more knowledge points
    that total still needs beyond what is in hand and the estimated further runs (None while no
    run has been completed, since there is no earning rate yet)."""
    pinned = set(meta["pinned_skills"])
    rate = average_knowledge_per_run()
    rows, running = [], 0
    for skill_id in purchase_route():
        cost = SKILLS[skill_id]["cost"]
        running += cost
        short = max(0, running - skill_tree.knowledge_points)
        if short == 0:
            runs = 0
        elif rate and rate > 0:
            runs = max(1, math.ceil(short / rate))
        else:
            runs = None
        rows.append(
            {
                "skill_id": skill_id,
                "label": SKILLS[skill_id]["label"],
                "cost": cost,
                "running_total": running,
                "short": short,
                "runs": runs,
                "prerequisite_only": skill_id not in pinned,
            }
        )
    return rows


def route_row_text(index, row):
    when = "affordable now" if row["runs"] == 0 else (
        "complete a run for an estimate" if row["runs"] is None
        else f"about {row['runs']} more run{'s' if row['runs'] != 1 else ''}"
    )
    extra = " (needed first)" if row["prerequisite_only"] else ""
    return (
        f"{index}. {row['label']}{extra}: {row['cost']} knowledge, running total {row['running_total']}, "
        f"{when}"
    )


def route_summary_text():
    rows = route_rows()
    if not rows:
        return "Pin skills to plan a route."
    total = rows[-1]["running_total"]
    have = skill_tree.knowledge_points
    last = rows[-1]
    if last["runs"] == 0:
        ending = "you can afford the whole route now."
    elif last["runs"] is None:
        ending = "complete a run to estimate how long it will take."
    else:
        ending = f"about {last['runs']} more run{'s' if last['runs'] != 1 else ''} at your average of {average_knowledge_per_run():.1f} knowledge per run."
    return f"Route total {total} knowledge, {have} in hand: {ending}"


def render_route_planner():
    panel = _el("route-planner")
    if panel is None:
        return
    rows = route_rows()
    panel.hidden = not rows
    listing = _el("route-list")
    if listing is not None:
        listing.innerHTML = ""
        for index, row in enumerate(rows, start=1):
            item = document.createElement("li")
            item.className = "route-step" + (" route-step--prereq" if row["prerequisite_only"] else "")
            item.innerText = route_row_text(index, row)
            listing.appendChild(item)
    summary = _el("route-summary")
    if summary is not None:
        summary.innerText = route_summary_text()
    title = _el("route-planner-summary")
    if title is not None:
        title.innerText = f"Purchase route ({len(rows)} step{'s' if len(rows) != 1 else ''})" if rows else "Purchase route"


# ---- E-5: plain-text schedule --------------------------------------------------
def schedule_plain_text(run_state=None):
    """The whole schedule as words, one line, no colours or icons needed."""
    run_state = run_state or run
    parts = []
    for entry in schedule_strip_entries(run_state):
        if entry["state"] == "done":
            note = f"faced, {entry['damage']:.0f} damage"
        elif entry["state"] == "next":
            note = f"next, about {entry['damage']:.0f} damage"
        else:
            note = f"upcoming, about {entry['damage']:.0f} damage"
        parts.append(f"{entry['number']}. {entry['label']} ({note})")
    return "; ".join(parts) + "."


def render_schedule_text():
    text_el = _el("schedule-text")
    if text_el is not None:
        text_el.innerText = schedule_plain_text(run)


# ---- E-4: shareable run codes (shared/run_code.py) and challenge runs -------------------------------
# A run code carries: a seed (5 characters), a mode word (a-z0-9, up to 8), a score and two numbers.
# Aftermath uses them like this:
#   mode   the scenario word ("classic", "coastal", ..., "heatsea"), plus a trailing "x" for an
#          Extended Run, or "custom" for a player-built schedule;
#   seed   the severity DRAW (a whole number written in the seed alphabet; the sender's run number,
#          because severity is a fixed pattern per run number), or, for "custom", the schedule itself
#          (up to 7 events, 3 bits each, with a leading 1 so the length is kept);
#   score  the sender's resources left; stats: their adjusted score (E-9) and the damage they took.
# A friend who pastes the code can PLAY the same schedule as a challenge run: the same events in the
# same order struck by the same draw pattern at the plain severity band, with their own skill tree,
# starting bonuses and society memory switched off, so both of you start from a fresh settlement.
# Challenge runs earn no knowledge and write nothing to the run history; they count toward a visible
# "challenge runs finished" tally and a best score per code.
RUN_CODE_GAME = "aftermath"
SCENARIO_CODE_WORD = {
    "classic": "classic", "coastal": "coastal", "inland": "inland", "urban": "urban",
    "san_francisco": "sanfran", "houston": "houston", "phoenix": "phoenix", "chicago": "chicago",
    "heat_season": "heatsea",
}
CODE_WORD_SCENARIO = {word: scenario for scenario, word in SCENARIO_CODE_WORD.items()}
CUSTOM_CODE_WORD = "custom"
# The position of an event type in a custom schedule's seed. Only ever APPEND here (and the digit
# base of 8 leaves room for exactly one more), because shared codes would otherwise change meaning.
EVENT_CODE_ORDER = (
    "flood", "heatwave", "storm", "supply_chain", "infrastructure_failure", "civil_unrest", "heat_mortality",
)


def run_code_mode_names():
    """Mode word -> display name, for the page's 'Their run: ...' line (read through pyodide)."""
    names = {}
    for word, scenario in CODE_WORD_SCENARIO.items():
        label = SCENARIOS[scenario]["label"]
        names[word] = label
        names[word + "x"] = f"{label}, extended"
    names[CUSTOM_CODE_WORD] = "Custom schedule"
    return names


def seed_text_for_int(number):
    """The 5-character seed for a whole number (base 31, the seed alphabet), as AFTERMATH-XXXXX."""
    base = len(shared_seed.ALPHABET)
    if not isinstance(number, int) or number < 0 or number >= base ** shared_seed.CODE_LEN:
        return None
    chars = []
    for _ in range(shared_seed.CODE_LEN):
        number, remainder = divmod(number, base)
        chars.append(shared_seed.ALPHABET[remainder])
    return f"{shared_seed.prefix_for(RUN_CODE_GAME)}-{''.join(reversed(chars))}"


def int_from_seed_text(text):
    code = str(text).split("-")[-1]
    number = 0
    for ch in code:
        number = number * len(shared_seed.ALPHABET) + shared_seed.ALPHABET.index(ch)
    return number


def custom_schedule_number(events):
    """A custom schedule as one whole number: a leading 1 then each event's position in base 8."""
    if not events or len(events) > CUSTOM_MAX_EVENTS or any(e not in EVENT_CODE_ORDER for e in events):
        return None
    number = 1
    for event_type in events:
        number = number * 8 + EVENT_CODE_ORDER.index(event_type)
    return number


def custom_schedule_from_number(number):
    """The inverse; None unless it is a well-formed schedule of CUSTOM_MIN_EVENTS..CUSTOM_MAX_EVENTS."""
    digits = []
    while number > 1:
        number, digit = divmod(number, 8)
        if digit >= len(EVENT_CODE_ORDER):
            return None
        digits.append(EVENT_CODE_ORDER[digit])
    if number != 1 or not CUSTOM_MIN_EVENTS <= len(digits) <= CUSTOM_MAX_EVENTS:
        return None
    return list(reversed(digits))


def run_code_mode(run_state):
    if run_state.custom_events:
        return CUSTOM_CODE_WORD
    return SCENARIO_CODE_WORD[run_state.scenario] + ("x" if run_state.extended else "")


def run_code_seed_number(run_state):
    if run_state.custom_events:
        return custom_schedule_number(run_state.custom_events)
    return run_state.draw if run_state.normalised else run_state.run_number


def run_code_fields(run_state=None):
    """The fields for shared/run-code.js's copy box (the page reads this through pyodide): a FINISHED
    run only, else None. The score is the resources left; the two stats are the adjusted score and
    the damage taken."""
    run_state = run_state or run
    if not run_state.is_complete():
        return None
    seed_text = seed_text_for_int(run_code_seed_number(run_state))
    if seed_text is None:
        return None
    return {
        "seed": seed_text,
        "mode": run_code_mode(run_state),
        "score": int(round(max(0.0, run_state.run_score()))),
        "stats": [
            int(round(adjusted_score(run_state.run_score(), run_state.event_log))),
            int(round(max(0.0, run_state.damage_taken))),
        ],
    }


def make_run_code(run_state=None):
    fields = run_code_fields(run_state)
    if fields is None:
        return None
    return shared_run_code.encode({"game": RUN_CODE_GAME, **fields})


def schedule_code(events):
    """A code for a schedule alone (no result), to hand a friend before anyone has played it."""
    number = custom_schedule_number(events)
    seed_text = seed_text_for_int(number) if number is not None else None
    if seed_text is None:
        return None
    return shared_run_code.encode({"game": RUN_CODE_GAME, "seed": seed_text, "mode": CUSTOM_CODE_WORD})


def challenge_spec(decoded):
    """(spec, error) from a decoded run code: what to play. spec has scenario, extended, draw and
    custom_events."""
    if not decoded.get("ok"):
        return None, decoded.get("message") or "That is not a run code."
    mode, seed_text = decoded.get("mode", ""), decoded.get("seed", "")
    if not seed_text:
        return None, "That code has no schedule to play. Ask for a code from a finished run or a saved schedule."
    number = int_from_seed_text(seed_text)
    if mode == CUSTOM_CODE_WORD:
        events = custom_schedule_from_number(number)
        if events is None:
            return None, "That custom schedule code is not valid."
        return {"scenario": DEFAULT_SCENARIO, "extended": False, "draw": 1, "custom_events": events}, ""
    extended = False
    word = mode
    if word not in CODE_WORD_SCENARIO and word.endswith("x") and word[:-1] in CODE_WORD_SCENARIO:
        word, extended = word[:-1], True
    if word not in CODE_WORD_SCENARIO:
        return None, "That code is for a mode this version of Aftermath does not know."
    return {"scenario": CODE_WORD_SCENARIO[word], "extended": extended, "draw": number, "custom_events": None}, ""


def _challenge_info(decoded):
    stats = decoded.get("stats") or []
    return {
        "code": decoded["code"],
        "their_score": decoded.get("score"),
        "their_adjusted": stats[0] if len(stats) > 0 else None,
        "their_damage": stats[1] if len(stats) > 1 else None,
    }


def challenge_run_from_code(code):
    """(RunState, error) for a pasted code; the run is NOT installed."""
    decoded = shared_run_code.decode(code, RUN_CODE_GAME)
    spec, error = challenge_spec(decoded)
    if spec is None:
        return None, error
    state = RunState(
        run_number=max(1, highest_awarded_run),
        extended=spec["extended"],
        scenario=spec["scenario"],
        normalised=True,
        draw=spec["draw"],
        custom_events=spec["custom_events"],
        custom_name="Friend's schedule" if spec["custom_events"] else None,
        challenge=_challenge_info(decoded),
    )
    return state, ""


challenge_status_text = ""


def _reset_run_ui_state():
    """What starting or swapping a run clears (shared by new runs, challenges and built schedules)."""
    global callout_message, last_knowledge_preview
    callout_message = ""
    last_knowledge_preview = None
    document.getElementById("copy-run-summary-status").innerText = ""
    document.getElementById("copy-run-summary-area").hidden = True
    announce("")


def start_challenge(code):
    """Plays a friend's run code as a challenge run. Only between runs (a finished run or one with
    no event faced yet), so nothing in progress is ever thrown away. Returns the message shown."""
    global run, challenge_status_text
    if not (run.is_complete() or run.event_index == 0):
        message = "Finish your current run first (or save it with the Save button), then play the challenge."
    else:
        state, error = challenge_run_from_code(code)
        if state is None:
            message = error
        else:
            run = state
            _reset_run_ui_state()
            message = (
                f"Challenge started: {len(run.schedule)} events, your skills and memory are switched off, "
                "no knowledge is earned."
            )
    challenge_status_text = message
    render()
    announce(message)
    return message


def leave_challenge(event=None):
    """Drops an unfinished challenge and starts the next normal run."""
    global run, challenge_status_text
    if not run.normalised:
        return
    extended = _el("extended-run-toggle")
    scenario = _el("scenario-select")
    run = RunState(
        run_number=highest_awarded_run + 1,
        extended=bool(extended.checked) if extended is not None else False,
        scenario=scenario.value if scenario is not None and scenario.value in SCENARIOS else DEFAULT_SCENARIO,
    )
    _reset_run_ui_state()
    challenge_status_text = "Left the challenge: back to your own settlement."
    render()


def _note_challenge_result(run_state):
    """A finished challenge counts toward the visible tally and keeps the best score per code."""
    meta["challenge_runs"] += 1
    info = run_state.challenge or {}
    code = info.get("code")
    if code:
        score = int(round(max(0.0, run_state.run_score())))
        best = meta["challenge_best"]
        best[code] = max(score, best.get(code, 0))
        while len(best) > CHALLENGE_BEST_MAX:
            best.pop(next(iter(best)))
    save_meta()


def challenge_result_text(run_state):
    info = run_state.challenge or {}
    mine = int(round(run_state.run_score()))
    text = (
        f"Challenge finished: you ended with {mine} resources ({adjusted_text(run_state.run_score(), run_state.event_log)}). "
    )
    theirs = info.get("their_score")
    if theirs is not None:
        extra = f", {info['their_adjusted']} adjusted" if info.get("their_adjusted") is not None else ""
        text += (
            f"Their run ended with {theirs}{extra}. They played with their own skill tree and you started fresh, "
            "so read it as a friendly note, not a ranking. "
        )
    return text + "Challenge runs earn no knowledge and leave your history alone."


def challenge_stats_text():
    played = meta["challenge_runs"]
    text = f"Challenge runs finished: {played}."
    if run.normalised and run.challenge:
        best = meta["challenge_best"].get(run.challenge.get("code"))
        if best is not None:
            text += f" Your best on this code: {best}."
    return text


def challenge_banner_text(run_state=None):
    run_state = run_state or run
    if not run_state.normalised:
        return ""
    info = run_state.challenge or {}
    theirs = f" Their run ended with {info['their_score']}." if info.get("their_score") is not None else ""
    return (
        f"Challenge run: a friend's schedule, {len(run_state.schedule)} events, with your skill tree and "
        f"memory switched off. No knowledge is earned.{theirs}"
    )


def render_challenge():
    banner = _el("challenge-banner")
    if banner is not None:
        banner.innerText = challenge_banner_text()
        banner.hidden = not run.normalised
    leave = _el("challenge-leave-button")
    if leave is not None:
        leave.hidden = not (run.normalised and not run.is_complete())
    stats = _el("challenge-stats")
    if stats is not None:
        stats.innerText = challenge_stats_text()
    status = _el("challenge-status")
    if status is not None:
        status.innerText = challenge_status_text
    wrap = _el("run-end-code-wrap")
    if wrap is not None:
        wrap.hidden = not run.is_complete()
    note = _el("run-end-code-note")
    if note is not None:
        note.innerText = (
            "" if run.is_complete() else "Finish a run to get its run code, then copy it for a friend."
        )
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    update = getattr(window, "aftermathRunCodeUpdate", None)
    if update is not None:
        try:
            update()
        except Exception:
            pass


# ---- E-13: schedule builder --------------------------------------------------------------------------
builder_draft = []
builder_status_text = ""


def builder_total_damage(events=None):
    return sum(EVENT_BASE_DAMAGE[e] for e in (builder_draft if events is None else events))


def builder_knowledge_share(events=None):
    events = builder_draft if events is None else events
    reference = sum(EVENT_BASE_DAMAGE[e] for e in EVENT_SCHEDULE)
    return min(1.0, builder_total_damage(events) / reference) if events else 0.0


def builder_summary_text():
    count = len(builder_draft)
    if not count:
        return f"Empty. Add {CUSTOM_MIN_EVENTS} to {CUSTOM_MAX_EVENTS} events from the library."
    return (
        f"{count} of {CUSTOM_MAX_EVENTS} events, {builder_total_damage():.0f} base damage "
        f"(Classic mix: {sum(EVENT_BASE_DAMAGE[e] for e in EVENT_SCHEDULE):.0f}). "
        f"A run on it earns {builder_knowledge_share() * 100:.0f}% of the usual knowledge."
    )


def builder_add(event_type):
    if event_type not in EVENT_LABEL or len(builder_draft) >= CUSTOM_MAX_EVENTS:
        return False
    builder_draft.append(event_type)
    return True


def builder_remove(index):
    if 0 <= index < len(builder_draft):
        builder_draft.pop(index)
        return True
    return False


def builder_move(index, delta):
    target = index + delta
    if 0 <= index < len(builder_draft) and 0 <= target < len(builder_draft):
        builder_draft[index], builder_draft[target] = builder_draft[target], builder_draft[index]
        return True
    return False


def _custom_named(name):
    key = _clean_name(name, CUSTOM_NAME_MAX).casefold()
    for entry in meta["custom_schedules"]:
        if entry["name"].casefold() == key:
            return entry
    return None


def save_custom_schedule(name, events=None):
    """Saves the draft (or `events`) under a name; the same name (any case) is replaced."""
    events = list(builder_draft if events is None else events)
    name = _clean_name(name, CUSTOM_NAME_MAX)
    if not name:
        return False, "Give the schedule a name."
    if not CUSTOM_MIN_EVENTS <= len(events) <= CUSTOM_MAX_EVENTS:
        return False, f"A schedule needs {CUSTOM_MIN_EVENTS} to {CUSTOM_MAX_EVENTS} events."
    existing = _custom_named(name)
    if existing is None and len(meta["custom_schedules"]) >= CUSTOM_SCHEDULES_MAX:
        return False, f"You can keep up to {CUSTOM_SCHEDULES_MAX} saved schedules. Delete one first."
    entry = {"name": name, "events": events}
    if existing is None:
        meta["custom_schedules"].append(entry)
    else:
        meta["custom_schedules"][meta["custom_schedules"].index(existing)] = entry
    save_meta()
    return True, f"{'Updated' if existing else 'Saved'} schedule {name} ({len(events)} events)."


def delete_custom_schedule(name):
    existing = _custom_named(name)
    if existing is None:
        return False
    meta["custom_schedules"].remove(existing)
    save_meta()
    return True


def start_custom_run(name):
    """Runs a saved schedule as a normal run (your tree applies; it is tagged 'custom schedule'),
    only between runs. Returns the message shown."""
    global run
    entry = _custom_named(name)
    if entry is None:
        return "That schedule no longer exists."
    if not (run.is_complete() or run.event_index == 0):
        return "Finish your current run first (or save it with the Save button), then run a custom schedule."
    number = max(run.run_number, highest_awarded_run) + 1 if run.is_complete() else run.run_number
    if run.normalised:
        number = highest_awarded_run + 1
    run = RunState(run_number=number, custom_events=entry["events"], custom_name=entry["name"])
    _reset_run_ui_state()
    return f"Started a run on {entry['name']}: {len(entry['events'])} events. It is tagged as a custom schedule."


def _builder_message(message):
    global builder_status_text
    builder_status_text = message
    render()
    announce(message)


def _make_library_handler(event_type):
    def handler(event=None):
        if builder_add(event_type):
            _builder_message(f"Added {EVENT_LABEL[event_type]}. {len(builder_draft)} of {CUSTOM_MAX_EVENTS} events.")
        else:
            _builder_message(f"The schedule is full: {CUSTOM_MAX_EVENTS} events at most.")
    return handler


def on_builder_clear(event=None):
    del builder_draft[:]
    _builder_message("Cleared the draft.")


def on_builder_save(event=None):
    name_el = _el("builder-name-input")
    ok, message = save_custom_schedule(name_el.value if name_el is not None else "")
    _builder_message(message)


def on_builder_draft_event(event=None):
    target = getattr(event, "target", None)
    if target is None:
        return
    action, raw = target.getAttribute("data-action"), target.getAttribute("data-index")
    if not action or raw is None or not str(raw).isdigit():
        return
    index = int(raw)
    if action == "remove" and builder_remove(index):
        _builder_message(f"Removed event {index + 1}. {len(builder_draft)} of {CUSTOM_MAX_EVENTS} events.")
        _focus(_el("builder-draft"))
    elif action in ("up", "down") and builder_move(index, -1 if action == "up" else 1):
        _builder_message(f"Moved event {index + 1} {action}.")
        _focus(_el("builder-draft"))


def on_builder_saved_event(event=None):
    target = getattr(event, "target", None)
    if target is None:
        return
    action, name = target.getAttribute("data-action"), target.getAttribute("data-name")
    entry = _custom_named(name) if name else None
    if not action or entry is None:
        return
    if action == "load":
        builder_draft[:] = list(entry["events"])
        name_el = _el("builder-name-input")
        if name_el is not None:
            name_el.value = entry["name"]
        _builder_message(f"Loaded {entry['name']} into the draft.")
    elif action == "run":
        message = start_custom_run(entry["name"])
        _builder_message(message)
    elif action == "delete":
        delete_custom_schedule(entry["name"])
        _builder_message(f"Deleted schedule {entry['name']}.")
    elif action == "share":
        code = schedule_code(entry["events"])
        area = _el("builder-code")
        if area is not None and code:
            area.hidden = False
            area.value = code
            _focus(area)
            try:
                area.select()
            except Exception:
                pass
        copied = bool(code) and _copy_to_clipboard(code)
        _builder_message(
            f"Copied the code for {entry['name']}: a friend can paste it under Run codes and challenges." if copied
            else f"The code for {entry['name']} is in the box below: copy it and send it to a friend."
        )


def build_library_buttons():
    holder = _el("builder-library")
    if holder is None:
        return
    holder.innerHTML = ""
    for event_type in EVENT_CODE_ORDER:
        button = document.createElement("button")
        button.className = f"secondary builder-library-button event-category--{EVENT_CATEGORY[event_type]}"
        button.setAttribute("type", "button")
        button.setAttribute("data-event", event_type)
        button.innerText = f"+ {EVENT_ICON[event_type]} {EVENT_LABEL[event_type]}"
        button.addEventListener("click", create_proxy(_make_library_handler(event_type)))
        holder.appendChild(button)


def render_builder():
    holder = _el("builder-library")
    full = len(builder_draft) >= CUSTOM_MAX_EVENTS
    if holder is not None:
        for button in holder.children:
            button.disabled = full
    draft = _el("builder-draft")
    if draft is not None:
        draft.innerHTML = ""
        for index, event_type in enumerate(builder_draft):
            item = document.createElement("li")
            item.className = f"builder-item event-category--{EVENT_CATEGORY[event_type]}"
            label = document.createElement("span")
            label.className = "builder-item-label"
            label.innerText = f"{EVENT_ICON[event_type]} {EVENT_LABEL[event_type]} ({EVENT_BASE_DAMAGE[event_type]:.0f})"
            item.appendChild(label)
            for action, text, aria in (("up", "↑", "Move up"), ("down", "↓", "Move down"), ("remove", "✕", "Remove")):
                button = document.createElement("button")
                button.className = "secondary builder-item-button"
                button.setAttribute("type", "button")
                button.setAttribute("data-action", action)
                button.setAttribute("data-index", str(index))
                button.setAttribute("aria-label", f"{aria} event {index + 1}, {EVENT_LABEL[event_type]}")
                button.innerText = text
                button.disabled = (action == "up" and index == 0) or (action == "down" and index == len(builder_draft) - 1)
                item.appendChild(button)
            draft.appendChild(item)
    summary = _el("builder-summary")
    if summary is not None:
        summary.innerText = builder_summary_text()
    save = _el("builder-save-button")
    if save is not None:
        save.disabled = len(builder_draft) < CUSTOM_MIN_EVENTS
    clear = _el("builder-clear-button")
    if clear is not None:
        clear.disabled = not builder_draft
    saved = _el("builder-saved-list")
    if saved is not None:
        saved.innerHTML = ""
        if not meta["custom_schedules"]:
            empty = document.createElement("li")
            empty.innerText = "No saved schedules yet."
            saved.appendChild(empty)
        can_run = run.is_complete() or run.event_index == 0
        for entry in meta["custom_schedules"]:
            item = document.createElement("li")
            item.className = "builder-saved-item"
            label = document.createElement("span")
            label.className = "builder-item-label"
            label.innerText = f"{entry['name']}: " + " → ".join(EVENT_LABEL[e] for e in entry["events"])
            item.appendChild(label)
            for action, text in (("run", "Run it"), ("load", "Edit"), ("share", "Code"), ("delete", "Delete")):
                button = document.createElement("button")
                button.className = "secondary builder-item-button"
                button.setAttribute("type", "button")
                button.setAttribute("data-action", action)
                button.setAttribute("data-name", entry["name"])
                button.setAttribute("aria-label", f"{text}: {entry['name']}")
                button.innerText = text
                button.disabled = action == "run" and not can_run
                item.appendChild(button)
            saved.appendChild(item)
    status = _el("builder-status")
    if status is not None:
        status.innerText = builder_status_text


# ---- GE-18 / E-15 handlers ---------------------------------------------
def on_undo_allocation(event=None):
    if run.undo_last_allocation():
        announce(f"Undid the last allocation. Resources {run.resources:.0f}, resilience {run.resilience_capacity}, growth {run.growth_capacity}.")
    render()


def _make_step_handler(step):
    def handler(event=None):
        set_invest_step(step)
        render()
    return handler


def render():
    render_info_page()
    update_achievements_display()
    render_past_runs_panel()
    render_codex_panel()
    render_stats_panel()
    render_damage_popup()
    update_tab_title()
    update_changelog_display()
    document.getElementById("legacy-display").innerText = legacy_message()
    document.getElementById("societal-memory-display").innerText = societal_memory_message()
    render_mentor()
    render_real_world()
    render_schedule_strip()
    render_schedule_text()  # E-5
    render_damage_waterfall()
    render_skill_filters()  # E-19
    render_presets()  # E-25
    render_route_planner()  # E-3
    render_builder()  # E-13
    render_skill_move()  # AN-13
    render_challenge()  # E-4
    document.getElementById("curriculum-display").innerText = curriculum_message()
    document.getElementById("resources-display").innerText = f"Resources: {run.resources:.0f}"
    document.getElementById("resilience-display").innerText = f"Resilience: {run.resilience_capacity}"
    document.getElementById("growth-display").innerText = (
        f"Growth: {run.growth_capacity} (+{growth_income_now(run.growth_capacity)} resources/event)"
    )
    document.getElementById("runs-completed-display").innerText = runs_completed_text()  # E4/E25
    document.getElementById("settlement-badge-toughest").classList.remove("settlement-badge--earned")
    badge = document.getElementById("settlement-badge-toughest")
    badge.title = toughest_badge_title()  # E-9
    if toughest_survived_run_badge_earned():  # E12
        badge.classList.add("settlement-badge--earned")
    callout_el = document.getElementById("callout-display")
    callout_el.innerText = callout_message
    callout_el.hidden = not callout_message
    memory_el = document.getElementById("generational-memory-display")
    memory_text = generational_memory_text(run)
    memory_el.innerText = memory_text
    memory_el.hidden = not memory_text
    document.getElementById("extended-run-toggle-label").innerText = (
        f"Extended Run ({len(EVENT_SCHEDULE) * 2} events instead of {len(EVENT_SCHEDULE)})"  # E6
    )

    # E4: legacy-history chips (additive to the legacy-display flavor line
    # above).
    history_panel = document.getElementById("legacy-history-panel")
    history_panel.innerHTML = ""
    for entry in legacy_history_summary():
        chip = document.createElement("span")
        chip.className = "legacy-history-chip"
        chip.innerText = f"{entry['icon']} {entry['label']} ×{entry['count']}"
        history_panel.appendChild(chip)

    # V-CD-6: legacy weathering scars -- one CSS tier class per category,
    # driven by the same legacy_event_counts as the chip row above.
    for category, tier in legacy_scar_tiers().items():
        scar_el = document.getElementById(f"settlement-legacy-scar-{category}")
        if scar_el is None:
            continue  # a cached older page without this category's scar (service worker serves stale HTML once)
        for t in (1, 2, 3):
            scar_el.classList.remove(f"settlement-legacy-scar--tier-{t}")
        if tier:
            scar_el.classList.add(f"settlement-legacy-scar--tier-{tier}")

    run_summary_panel = document.getElementById("run-summary-panel")

    if run.is_complete():
        document.getElementById("progress-display").innerText = "Run complete"
        document.getElementById("next-event-display").innerText = "No more events this run."
        document.getElementById("expected-damage-display").innerText = ""
        document.getElementById("flawless-hint-display").innerText = ""
        document.getElementById("knowledge-preview-display").innerText = ""
        document.getElementById("run-summary-display").innerText = (
            challenge_result_text(run) if run.normalised else
            f"Score: {run.run_score():.0f} — "
            f"earned {run.knowledge_points_earned()} resilience knowledge point"
            f"{'s' if run.knowledge_points_earned() != 1 else ''}."
        )
        # E11: a proper end-of-run summary -- final stats plus the exact
        # event-by-event breakdown, not just the one-line score above.
        run_summary_panel.hidden = False
        run_summary_panel.innerHTML = ""
        stats = document.createElement("p")
        stats.className = "run-summary-stats"
        stats.innerText = (
            f"Final resilience: {run.resilience_capacity} · Final growth: {run.growth_capacity} · "
            f"Total damage taken: {run.damage_taken:.0f} · Score {run.run_score():.0f}, "
            f"{adjusted_text(run.run_score(), run.event_log)}"  # E-9
        )
        run_summary_panel.appendChild(stats)
        _render_event_breakdown_lines(run_summary_panel, run.event_log)
        # E-23: where the knowledge points came from.
        breakdown = document.createElement("div")
        breakdown.className = "knowledge-breakdown"
        breakdown_heading = document.createElement("p")
        breakdown_heading.className = "knowledge-breakdown-heading"
        breakdown_heading.innerText = "Knowledge earned this run"
        breakdown.appendChild(breakdown_heading)
        for text in knowledge_breakdown_lines(run):
            line = document.createElement("p")
            line.className = "knowledge-breakdown-line"
            line.innerText = text
            breakdown.appendChild(line)
        if not run.normalised:  # E-4: a challenge run earns no knowledge, so no breakdown
            run_summary_panel.appendChild(breakdown)
        if not run.normalised and not epitaph_hidden():  # GE-21
            epitaph_el = document.createElement("p")
            epitaph_el.className = "run-epitaph"
            epitaph_el.innerText = epitaph_text(run)
            run_summary_panel.appendChild(epitaph_el)
        epilogue = extended_epilogue_text(run) if not run.normalised else ""
        if epilogue:
            epilogue_el = document.createElement("p")
            epilogue_el.className = "run-epilogue"
            epilogue_el.innerText = epilogue
            run_summary_panel.appendChild(epilogue_el)
    else:
        document.getElementById("run-summary-display").innerText = ""
        run_summary_panel.hidden = True
        run_summary_panel.innerHTML = ""
        document.getElementById("progress-display").innerText = (
            f"Event {run.event_index + 1} of {len(run.schedule)}"
        )
        next_type = run.next_event_type()
        next_event_el = document.getElementById("next-event-display")
        next_event_el.innerText = f"Next: {EVENT_ICON[next_type]} {EVENT_LABEL[next_type]}"
        next_event_el.className = f"status-line event-category--{EVENT_CATEGORY[next_type]}"

        # E8/E16: expected-damage-this-event preview, numeric severity band.
        damage, severity = expected_next_event_damage(run)
        expected_el = document.getElementById("expected-damage-display")
        low, high = expected_damage_range(run)
        expected_el.innerText = (
            f"Expected damage: ~{damage:.0f} ({severity:.2f}× severity, {severity_label(severity)}; "
            f"range {low:.0f}–{high:.0f})"
        )
        expected_el.className = f"status-line severity--{severity_label(severity)}"
        expected_el.title = (
            "Challenge runs use a fixed severity pattern shared with the friend who made the code."
            if run.normalised else severity_tooltip_text(run.run_number)
        )
        document.getElementById("flawless-hint-display").innerText = flawless_hint_text(run)  # GE-15

        # E20: a live preview of the knowledge points a run would award
        # if it ended right now.
        knowledge_now = run.knowledge_points_earned()
        preview_el = document.getElementById("knowledge-preview-display")
        preview_el.innerText = (
            "Challenge runs earn no knowledge points." if run.normalised else
            f"If the run ended now: {knowledge_now} knowledge point{'s' if knowledge_now != 1 else ''}"
            + knowledge_preview_detail(run)  # E-23
        )
        global last_knowledge_preview
        if last_knowledge_preview is not None and knowledge_now > last_knowledge_preview:
            _flash_element("knowledge-preview-display", 900, "knowledge-bump")  # E18
        last_knowledge_preview = knowledge_now

    last_event_el = document.getElementById("last-event-display")
    if run.event_log:
        last = run.event_log[-1]
        last_event_el.innerText = (
            f"Last: {EVENT_ICON[last['type']]} {EVENT_LABEL[last['type']]} "
            f"— {last['damage']:.0f} damage ({severity_label(last['severity'])} intensity)"
        )
        # E19: distinct visual intensity per event severity, alongside the
        # pre-existing weather/non-weather/social category class.
        last_event_el.className = (
            f"status-line event-category--{EVENT_CATEGORY[last['type']]} "
            f"severity--{severity_label(last['severity'])}"
        )
    else:
        last_event_el.innerText = ""
        last_event_el.className = "status-line"

    document.getElementById("mitigation-bar").style.width = f"{run.mitigation_fraction() * 100:.0f}%"

    resilience_button = document.getElementById("resilience-invest-button")
    resilience_button.innerText = resilience_button_label(run, invest_step)
    resilience_button.disabled = run.is_complete() or run.step_units("resilience", invest_step) < 1

    growth_button = document.getElementById("growth-invest-button")
    growth_button.innerText = growth_step_label(run, invest_step)
    growth_button.disabled = run.is_complete() or run.step_units("growth", invest_step) < 1

    for step in INVEST_STEPS:  # E-15
        step_button = document.getElementById(f"step-{'max' if step == 'max' else 'x' + str(step)}-button")
        step_button.setAttribute("aria-pressed", "true" if step == invest_step else "false")
        if step == invest_step:
            step_button.classList.add("selected")
        else:
            step_button.classList.remove("selected")
    undo_button = document.getElementById("undo-allocation-button")  # GE-18
    undo_button.innerText = f"↶ Undo ({run.undo_count()})"
    undo_button.disabled = run.undo_count() < 1 or run.is_complete()

    # E-24: the copy button is available once an event has been faced.
    document.getElementById("run-summary-actions").hidden = not run.event_log

    resolve_button = document.getElementById("resolve-event-button")
    resolve_button.disabled = run.is_complete()

    document.getElementById("new-run-button").hidden = not run.is_complete()
    render_save_health()  # E-30
    document.getElementById("extended-run-toggle-wrapper").hidden = not run.is_complete()
    # E17a: the scenario can be picked before a run's first event or between runs.
    document.getElementById("scenario-wrapper").hidden = (
        not (run.is_complete() or run.event_index == 0) or (run.normalised and not run.is_complete())
    )
    scenario_select = document.getElementById("scenario-select")
    if run.event_index == 0 and not run.is_complete():
        scenario_select.value = run.scenario
    document.getElementById("scenario-blurb").innerText = (
        f"Custom schedule: {run.custom_name or 'built by you'} ({len(run.schedule)} events)." if (run.custom_events and not run.is_complete())
        else SCENARIOS[scenario_select.value if scenario_select.value in SCENARIOS else run.scenario]["blurb"]
    )
    document.getElementById("progress-comparison-display").innerText = progress_message(
        progress_comparison()
    )

    streak_el = document.getElementById("improvement-streak-display")  # GE-22
    if streak_el is not None:
        streak_el.innerText = streak_text()
        streak_el.hidden = not streak_el.innerText

    # E17: toughest run yet.
    toughest = toughest_run_yet()
    toughest_el = document.getElementById("toughest-run-display")
    toughest_el.innerText = toughest_run_text() if toughest else ""

    document.getElementById("knowledge-points-display").innerText = (
        f"Resilience knowledge: {skill_tree.knowledge_points}"
    )

    # E9: visible "X/Y skills unlocked" progress summary.
    document.getElementById("skills-unlocked-display").innerText = (
        f"{len(skill_tree.unlocked)}/{len(SKILLS)} skills unlocked"
    )

    # E13: reset-skill-tree button (Z22: gated behind the shared
    # ConfirmDialog, which itself states the refund amount in its message
    # -- see on_reset_skill_tree()).
    reset_button = document.getElementById("reset-skill-tree-button")
    reset_button.disabled = not skill_tree.unlocked

    document.getElementById("pinned-skills-display").innerText = pinned_skills_text()  # E30b
    for skill_id, skill in SKILLS.items():
        eta_el = document.getElementById(f"skill-{skill_id}-eta")
        pin_button = document.getElementById(f"skill-{skill_id}-pin-button")
        if skill_id in skill_tree.unlocked:
            eta_el.innerText = ""
            pin_button.hidden = True
        else:
            eta_el.innerText = _eta_text(skill_id)  # E30a
            pin_button.hidden = False
            pinned = skill_id in meta["pinned_skills"]
            pin_button.innerText = "📌 Pinned" if pinned else "📍 Pin"
            pin_button.title = "Unpin this skill" if pinned else "Pin this skill to track how many runs until you can afford it"
        status_el = document.getElementById(f"skill-{skill_id}-status")
        practice_el = document.getElementById(f"skill-{skill_id}-practice")
        unlock_button = document.getElementById(f"skill-{skill_id}-unlock-button")
        practice_el.innerText = skill["real_practice"]
        helps_el = document.getElementById(f"skill-{skill_id}-helps")  # E-29
        if helps_el is not None:
            helps_el.innerText = skill_helps_text(skill_id)

        # E15: a settlement-art badge per unlocked skill.
        badge = document.getElementById(f"settlement-badge-{skill_id}")
        if skill_id in skill_tree.unlocked:
            badge.classList.add("settlement-badge--earned")
        else:
            badge.classList.remove("settlement-badge--earned")

        if skill_id in skill_tree.unlocked:
            status_el.innerText = f"{skill['label']} — unlocked ({skill['description']})"
            unlock_button.hidden = True
        else:
            missing = skill_tree.missing_prereqs(skill_id)
            if missing:
                # E3: branching/prerequisite structure -- tell the player
                # what's still locking this skill rather than just
                # disabling the button with no explanation.
                required = ", ".join(SKILLS[prereq]["label"] for prereq in missing)
                status_el.innerText = f"{skill['label']} — {skill['description']} (requires {required})"
                unlock_button.hidden = False
                unlock_button.innerText = f"Unlock ({skill['cost']})"
                unlock_button.disabled = True
            else:
                status_el.innerText = f"{skill['label']} — {skill['description']}"
                unlock_button.hidden = False
                unlock_button.innerText = f"Unlock ({skill['cost']})"
                unlock_button.disabled = not skill_tree.can_unlock(skill_id)


def on_invest_resilience(event=None):
    bought = run.invest_steps("resilience", invest_step)
    render()
    if bought:
        _flash_element("resources-display")
        announce(f"Invested in resilience x{bought}. Resilience {run.resilience_capacity}, resources {run.resources:.0f}.")
    _check_new_achievements_for_toast()


def on_invest_growth(event=None):
    bought = run.invest_steps("growth", invest_step)
    render()
    if bought:
        _flash_element("resources-display")
        announce(f"Invested in growth x{bought}. Growth {run.growth_capacity}, resources {run.resources:.0f}.")
    _check_new_achievements_for_toast()


# E-28: an optional "you still have resources" check before Face Next Event. Off by default
# (the Settings checkbox writes this key); it only ever asks, never changes a number.
CONFIRM_UNSPENT_STORAGE_KEY = "aftermath-confirm-unspent"


def confirm_unspent_enabled():
    return localStorage.getItem(CONFIRM_UNSPENT_STORAGE_KEY) == "true"


def unspent_confirm_message(run_state):
    """The question, naming what the unspent resources could still have bought, or
    None when there is nothing worth asking about (the run is over, or the
    resources cannot buy even one unit)."""
    if run_state.is_complete() or run_state.resources < min(RESILIENCE_COST, GROWTH_COST):
        return None
    resilience = run_state.step_units("resilience", "max")
    growth = int(run_state.resources // GROWTH_COST)
    options = []
    if resilience:
        options.append(f"up to {resilience} resilience")
    if growth:
        options.append(f"up to {growth} growth")
    return (
        f"Keep {run_state.resources:.0f} resources unspent? You could still buy {' or '.join(options)} "
        f"before {EVENT_LABEL[run_state.next_event_type()]} hits."
    )


def on_resolve_event(event=None):
    message = unspent_confirm_message(run) if confirm_unspent_enabled() else None
    if message is None:
        _resolve_event_now()
        return
    _confirm_dialog_ask(
        action_id="aftermath-unspent-resources",
        message=message,
        confirm_label="Face the event",
        on_confirm=_resolve_event_now,
        allow_skip=False,  # the Settings checkbox is the switch, so no hidden "don't ask again"
    )


def _resolve_event_now():
    before = len(run.event_log)
    run.resolve_next_event()
    _maybe_trigger_callouts(run)
    render()
    if len(run.event_log) > before:
        announce(event_announcement(run.event_log[-1]))  # E-5
    _check_new_achievements_for_toast()


def on_scenario_change(event=None):
    """E17a: picking a scenario before the current run's first event swaps its
    schedule immediately; between runs it is read by start_new_run(); once a
    run is underway the choice can no longer change it."""
    global run
    value = document.getElementById("scenario-select").value
    if value in SCENARIOS and run.event_index == 0 and not run.is_complete() and not run.normalised:
        run = RunState(run_number=run.run_number, extended=run.extended, scenario=value)
    render()


def start_new_run(event=None):
    """Starts a fresh run, reading current skill-tree bonuses — each run
    begins a little more capable than the last, per unlocked skills.

    Derives the new run_number from whichever is higher, the current run's
    own number or the persisted highest-awarded-run mark, not just the
    current run's number + 1. The current `run` can itself be a stale,
    reloaded snapshot (e.g. the player loaded an old still-in-progress save
    before starting anew) whose run_number sits behind runs that have
    since completed and been awarded elsewhere in the session -- basing
    the new number on it alone could hand out a run_number that's already
    in highest_awarded_run's past, silently blocking this genuinely new
    run's own completion payout later (see the double-award guard on
    resolve_next_event() above, and its dedicated test coverage in
    tests/test_save_system.py).

    E18: reads the extended-run-mode checkbox to decide whether the new
    run uses the doubled-length schedule (RunState's own `extended` flag)
    -- opt-in, and only ever read at the moment a new run starts, so it
    has no effect on a run already in progress."""
    global run, challenge_status_text
    _reset_run_ui_state()
    challenge_status_text = ""
    extended = document.getElementById("extended-run-toggle").checked
    scenario = document.getElementById("scenario-select").value
    # A finished challenge run never counted as a numbered run, so the next real one follows the last awarded.
    base = highest_awarded_run if run.normalised else run.run_number
    run = RunState(run_number=max(base, highest_awarded_run) + 1, extended=extended, scenario=scenario)
    render()
    _check_new_achievements_for_toast()


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Resilience skills unlocked", "value": skill_tree_strength(), "unit": f"of {len(SKILLS)}"},
        {"label": "Run number", "value": int(run.run_number), "unit": ""},
        {"label": "Resilience built this run", "value": int(run.resilience_capacity), "unit": ""},
    ]


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state()/load_state() cover Aftermath's in-memory *per-run* state
# only — the current RunState (run_number, event_index, resources,
# resilience_capacity, growth_capacity, damage_taken, event_log) — which
# is what needs to round-trip so a saved-and-reloaded run resumes at the
# exact point it was saved. The persistent skill tree (SkillTreeState),
# run_history, and legacy_events are deliberately NOT part of this
# round trip: per CLAUDE.md's Tech notes, those are a distinct,
# already-working persistence mechanism keyed to localStorage (not to a
# save code) that survives across runs and browser visits on its own.
# Folding them into this save system would mean a loaded save code could
# silently overwrite a browser's separately-accumulated skill tree with
# whatever it looked like at save time — the wrong behavior for state
# that's supposed to be permanent. A save code loaded on a different
# browser/device therefore resumes the exact in-progress run, but keeps
# whatever skill tree/legacy history (or lack of it) already exists
# locally — consistent with how that persistence already behaves
# independent of any one run.
def get_state():
    """Return the current run's in-memory state as a plain JSON-safe dict.
    `event_log` is deep-copied — it's a list of dicts, and a shallow copy
    would still alias it, so continued play after taking a "snapshot"
    would silently mutate the saved copy."""
    return {
        "run_number": run.run_number,
        "event_index": run.event_index,
        "resources": run.resources,
        "resilience_capacity": run.resilience_capacity,
        "growth_capacity": run.growth_capacity,
        "damage_taken": run.damage_taken,
        "event_log": copy.deepcopy(run.event_log),
        # E18: whether this run is using the doubled-length schedule.
        # Added after this save contract first shipped -- load_state()
        # below defaults it to False for any older save code that
        # predates the field, rather than the KeyError every other key
        # here deliberately gets.
        "extended": run.extended,
        **({"scenario": run.scenario} if run.scenario != DEFAULT_SCENARIO else {}),
        # E-4 / E-13: a challenge run keeps its run code (the schedule and draw are rebuilt from it) and a
        # run on a built schedule keeps the events and name. Absent for ordinary runs.
        **({"challenge_code": run.challenge["code"]} if run.normalised and run.challenge else {}),
        **({"custom_events": list(run.custom_events), "custom_name": run.custom_name or ""}
           if run.custom_events and not run.normalised else {}),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back by load_state() below.
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
        **({"event_badges": list(event_badges)} if event_badges else {}),
        # E9: a write-only number for the community resilience index (how many
        # resilience skills this player's tree has unlocked); never read back.
        "skill_tree_strength": skill_tree_strength(),
    }


# Direct key access (data["run_number"], etc.), no defensive handling --
# unlike SkillTreeState.load()'s try/except. This is intentional, not an
# oversight: a real save handed here always came from this same site's own
# get_state() via the save widget's fetch/PUT round trip, so a malformed
# payload means something upstream already went wrong, and a loud KeyError
# is preferable to silently starting a run in a half-restored state. Pinned
# by tests/test_save_system.py::test_load_state_on_a_malformed_dict_raises_rather_than_corrupting_the_run
# so this stays a deliberate choice, not something a future change reverts.
def load_state(data):
    """The exact inverse of get_state() — rebuilds the current run from a
    saved dict and re-renders so the UI reflects the loaded run
    immediately. Constructs a fresh RunState (which reads current
    skill-tree bonuses, same as starting any new run) and then overwrites
    every field with the saved values, so the restored run matches
    exactly what was saved regardless of the skill tree's state now."""
    global run
    # data.get(...) rather than data["extended"] -- see get_state()'s
    # comment on this one field: it postdates this save contract, and an
    # older save code simply never was an extended run.
    saved_scenario = data.get("scenario")
    restored = None
    if isinstance(data.get("challenge_code"), str):  # E-4: rebuild the challenge from its code
        restored, _error = challenge_run_from_code(data["challenge_code"])
        if restored is not None:
            restored.run_number = data["run_number"]
    if restored is None:
        custom = data.get("custom_events")
        restored = RunState(
            run_number=data["run_number"], extended=data.get("extended", False),
            scenario=saved_scenario if isinstance(saved_scenario, str) else DEFAULT_SCENARIO,
            custom_events=custom if isinstance(custom, list) else None,
            custom_name=data.get("custom_name") if isinstance(data.get("custom_name"), str) else None,
        )
    run = restored
    run.event_index = data["event_index"]
    run.resources = data["resources"]
    run.resilience_capacity = data["resilience_capacity"]
    run.growth_capacity = data["growth_capacity"]
    run.damage_taken = data["damage_taken"]
    run.event_log = copy.deepcopy(data["event_log"])
    global event_badges
    event_badges = _clean_event_badges(data.get("event_badges"))
    if event_badges:
        _season_hook("aftermathAdoptBadges", json.dumps(event_badges))
    render()
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1. Re-seed
    # the toast baseline instead of leaving it as-is, so a loaded save with
    # several achievements already earned doesn't flood the player with
    # toasts for all of them at once (same reasoning as setup()'s seed).
    _seed_achievement_toast_baseline()
    return True


def _make_pin_handler(skill_id):
    def handler(event=None):
        toggle_pin_skill(skill_id)
        render()
    return handler


def on_settlement_name_change(event=None):
    set_settlement_name(document.getElementById("settlement-name-input").value)
    render()


def render_skill_move():
    """AN-13: the "Move a point" panel: one owned skill to another, for SKILL_MOVE_FEE knowledge."""
    panel = _el("skill-move")
    if panel is None:
        return
    owned = [s for s in SKILLS if s in skill_tree.unlocked]
    panel.hidden = not owned
    from_select, to_select = _el("skill-move-from"), _el("skill-move-to")
    if from_select is None or to_select is None:
        return
    keep_from, keep_to = from_select.value, to_select.value
    from_select.innerHTML = ""
    to_select.innerHTML = ""
    for skill_id in owned:
        option = document.createElement("option")
        option.value = skill_id
        option.innerText = f"{SKILLS[skill_id]['label']} (costs {SKILLS[skill_id]['cost']})"
        from_select.appendChild(option)
    for skill_id in SKILLS:
        if skill_id in skill_tree.unlocked:
            continue
        option = document.createElement("option")
        option.value = skill_id
        option.innerText = f"{SKILLS[skill_id]['label']} (costs {SKILLS[skill_id]['cost']})"
        to_select.appendChild(option)
    unowned = [s for s in SKILLS if s not in skill_tree.unlocked]
    from_select.value = keep_from if keep_from in owned else (owned[0] if owned else "")
    to_select.value = keep_to if keep_to in unowned else (unowned[0] if unowned else "")
    ok, reason = skill_tree.move_check(from_select.value, to_select.value) if owned and to_select.value else (False, "Nothing to move to.")
    button = _el("skill-move-button")
    if button is not None:
        button.disabled = not ok
    status = _el("skill-move-status")
    if status is not None and not skill_move_message:
        status.innerText = (f"Moving costs {SKILL_MOVE_FEE} knowledge on top of the difference in price. "
                            + ("" if ok else reason))


skill_move_message = ""


def on_skill_move(event=None):
    global skill_move_message
    from_id = _el("skill-move-from").value
    to_id = _el("skill-move-to").value
    if skill_tree.move(from_id, to_id):
        skill_move_message = f"Moved from {SKILLS[from_id]['label']} to {SKILLS[to_id]['label']}. Knowledge left: {skill_tree.knowledge_points}."
        announce(skill_move_message)
    else:
        skill_move_message = skill_tree.move_check(from_id, to_id)[1] or "That move is not possible."
    status = _el("skill-move-status")
    if status is not None:
        status.innerText = skill_move_message
    render()
    skill_move_message = ""


def on_skill_move_select(event=None):
    global skill_move_message
    skill_move_message = ""
    render_skill_move()


def _make_unlock_handler(skill_id):
    def handler(event=None):
        unlocked = skill_tree.unlock(skill_id)
        render()
        if unlocked:
            _display_skill_unlock_toast(skill_id)
        _check_new_achievements_for_toast()
    return handler


def _listen(element_id, event_name, handler):
    element = _el(element_id)
    if element is not None:
        element.addEventListener(event_name, create_proxy(handler))


def _wire_round3_batch2():
    """Event wiring and one-time construction for E-19, E-25, E-30, E-13 and E-4 (each tolerates a
    cached older page that lacks the element)."""
    probe_storage()
    build_skill_filter_chips()
    build_library_buttons()
    _listen("skill-search-input", "input", on_skill_search)
    _listen("skill-filter-clear", "click", on_skill_filter_clear)
    _listen("preset-save-button", "click", on_preset_save)
    _listen("preset-from-turn-button", "click", on_preset_from_turn)
    _listen("preset-apply-button", "click", on_preset_apply)
    _listen("preset-select", "change", on_preset_select)
    for event_name in ("click",):
        _listen("preset-list", event_name, on_preset_list_event)
        _listen("builder-draft", event_name, on_builder_draft_event)
        _listen("builder-saved-list", event_name, on_builder_saved_event)
    _listen("builder-clear-button", "click", on_builder_clear)
    _listen("builder-save-button", "click", on_builder_save)
    _listen("save-health-export-button", "click", on_save_health_export)
    _listen("challenge-leave-button", "click", leave_challenge)
    _listen("skill-move-button", "click", on_skill_move)
    _listen("skill-move-from", "change", on_skill_move_select)
    _listen("skill-move-to", "change", on_skill_move_select)


def setup():
    document.getElementById("resilience-invest-button").addEventListener(
        "click", create_proxy(on_invest_resilience)
    )
    document.getElementById("growth-invest-button").addEventListener(
        "click", create_proxy(on_invest_growth)
    )
    document.getElementById("resolve-event-button").addEventListener(
        "click", create_proxy(on_resolve_event)
    )
    global mentor_enabled
    mentor_enabled = load_mentor_enabled()
    document.getElementById("mentor-toggle").addEventListener("change", create_proxy(on_toggle_mentor))
    document.getElementById("scenario-select").addEventListener("change", create_proxy(on_scenario_change))
    document.getElementById("new-run-button").addEventListener(
        "click", create_proxy(start_new_run)
    )
    for skill_id in SKILLS:
        document.getElementById(f"skill-{skill_id}-unlock-button").addEventListener(
            "click", create_proxy(_make_unlock_handler(skill_id))
        )
        document.getElementById(f"skill-{skill_id}-pin-button").addEventListener(
            "click", create_proxy(_make_pin_handler(skill_id))
        )
    document.getElementById("settlement-name-input").addEventListener(
        "change", create_proxy(on_settlement_name_change)
    )
    document.getElementById("settlement-name-input").value = meta["settlement_name"]
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("past-runs-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_past_runs)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    # E-22 / E-21 / E-20: one delegated handler for the whole Past Runs list, plus the controls.
    past_runs_list = document.getElementById("past-runs-list")
    if past_runs_list is not None:
        for event_name in ("click", "change"):
            past_runs_list.addEventListener(event_name, create_proxy(on_past_runs_event))
    for control_id in ("past-runs-sort", "past-runs-filter", "past-runs-archived"):
        control = document.getElementById(control_id)
        if control is not None:
            control.addEventListener("change", create_proxy(on_past_runs_controls_change))
    document.getElementById("reset-skill-tree-button").addEventListener(
        "click", create_proxy(on_reset_skill_tree)
    )
    document.getElementById("progress-export-button").addEventListener(
        "click", create_proxy(on_export_progress)
    )
    document.getElementById("progress-import-button").addEventListener(
        "click", create_proxy(on_import_progress)
    )
    document.getElementById("undo-allocation-button").addEventListener(
        "click", create_proxy(on_undo_allocation)
    )
    for step in INVEST_STEPS:
        button_id = f"step-{'max' if step == 'max' else 'x' + str(step)}-button"
        document.getElementById(button_id).addEventListener("click", create_proxy(_make_step_handler(step)))
    document.getElementById("codex-toggle-button").addEventListener("click", create_proxy(on_toggle_codex))
    document.getElementById("stats-toggle-button").addEventListener("click", create_proxy(on_toggle_stats))
    document.getElementById("copy-run-summary-button").addEventListener(
        "click", create_proxy(on_copy_run_summary)
    )
    document.getElementById("copy-run-summary-area").hidden = True
    _wire_round3_batch2()
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("skill-unlock-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
