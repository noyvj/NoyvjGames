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

import export_progress
import info_page
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


def event_severity(run_number, event_index, skill_strength=0):
    if run_number <= 1:
        return 1.0
    seed = (run_number * 97 + event_index * 31) % 100
    variation_min, variation_max = severity_bounds(skill_strength)
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
    localStorage.setItem(AWARDED_RUN_STORAGE_KEY, json.dumps(run_number))


def load_legacy_events():
    raw = localStorage.getItem(LEGACY_STORAGE_KEY)
    if not raw:
        return set()
    try:
        return set(json.loads(raw))
    except ValueError:
        return set()


def save_legacy_events(events):
    localStorage.setItem(LEGACY_STORAGE_KEY, json.dumps(sorted(events)))


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
    localStorage.setItem(SOCIETAL_MEMORY_STORAGE_KEY, json.dumps(sorted(categories)))


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
    localStorage.setItem(CURRICULUM_STORAGE_KEY, str(value))


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
    localStorage.setItem(RUN_HISTORY_STORAGE_KEY, json.dumps(history))


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
    localStorage.setItem(LEGACY_COUNTS_STORAGE_KEY, json.dumps(counts))


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
    localStorage.setItem(RUN_LOG_HISTORY_STORAGE_KEY, json.dumps(history))


# Small persistent "settlement meta" dict (E25 settlement name, E30b pinned
# skills, E8/E28 one-time-callout flags). Lives in localStorage next to the
# skill tree, same category and same reasoning (cross-run progress, not
# per-run save-widget state); safe defaults for every field so an older
# browser profile with no such key just gets the empty defaults.
META_STORAGE_KEY = "aftermath_meta_v1"
SETTLEMENT_NAME_MAX = 30


def _default_meta():
    return {
        "settlement_name": "",
        "pinned_skills": [],
        "seen_negative_tip": False,
        "seen_harsh_callout": False,
    }


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
    localStorage.setItem(META_STORAGE_KEY, json.dumps(meta))


meta = load_meta()


def starting_resources_bonus():
    return 50 if "community_reserves" in skill_tree.unlocked else 0


def starting_resilience_bonus():
    return 2 if "reinforced_infrastructure" in skill_tree.unlocked else 0


def early_warning_mitigation_bonus():
    return 0.10 if "early_warning" in skill_tree.unlocked else 0.0


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


def adaptive_growth_bonus():
    """E2: the fourth skill node -- a starting-growth-capacity bonus,
    mirroring reinforced_infrastructure/community_reserves' starting-stat
    shape but on the growth side instead of resilience/resources."""
    return 1 if "adaptive_growth" in skill_tree.unlocked else 0


def mutual_aid_mitigation_bonus():
    """E2: the fifth skill node -- flat mitigation like early_warning's,
    but gated behind E3's prereq structure (both foundational skills)."""
    return 0.05 if "mutual_aid_network" in skill_tree.unlocked else 0.0


# E1/E3: per-category damage reduction from the two specialization nodes.
CATEGORY_DAMAGE_BONUS = {
    "civic_preparedness": ("social", 0.35),
    "climate_hardening": ("weather", 0.20),
}


def category_mitigation_bonus(event_type):
    category = EVENT_CATEGORY.get(event_type)
    bonus = sum(
        amount
        for skill_id, (cat, amount) in CATEGORY_DAMAGE_BONUS.items()
        if cat == category and skill_id in skill_tree.unlocked
    )
    if category in societal_memory:
        bonus += SOCIETAL_MEMORY_BONUS[category]  # E29
    return bonus


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
    def __init__(self, run_number=1, extended=False, scenario=DEFAULT_SCENARIO):
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
        self.event_index = 0
        self.resources = STARTING_RESOURCES + starting_resources_bonus()
        self.resilience_capacity = starting_resilience_bonus()
        self.growth_capacity = adaptive_growth_bonus()
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
        else:
            self.growth_capacity -= units
            self.resources += GROWTH_COST * units
        return True

    # E-15: x1 / x5 / Max steps.
    def _raw_mitigation(self):
        return (
            self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
            + early_warning_mitigation_bonus()
            + mutual_aid_mitigation_bonus()
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

    def mitigation_fraction(self):
        from_resilience = self.resilience_capacity * RESILIENCE_MITIGATION_PER_UNIT
        return min(
            MAX_MITIGATION,
            from_resilience + early_warning_mitigation_bonus() + mutual_aid_mitigation_bonus(),
        )

    def mitigation_for(self, event_type):
        """Total damage reduction for one event: the general mitigation
        plus any category-specific specialization bonus, still capped at
        MAX_MITIGATION so nothing ever reaches full immunity."""
        return min(MAX_MITIGATION, self.mitigation_fraction() + category_mitigation_bonus(event_type))

    def resolve_next_event(self):
        """Applies growth income, then resolves the next scheduled event's
        damage (reduced by resilience mitigation). No-op once the run is
        complete."""
        if self.is_complete():
            return False

        self.resources += self.growth_capacity * GROWTH_INCOME_PER_UNIT

        event_type = self.schedule[self.event_index]
        severity = event_severity(self.run_number, self.event_index, skill_tree_strength())
        damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - self.mitigation_for(event_type))
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

        if self.is_complete():
            global highest_awarded_run
            if self.run_number > highest_awarded_run:
                skill_tree.add_knowledge(self.knowledge_points_earned())
                skill_tree.save()
                run_history.append(self.run_score())
                save_run_history(run_history)
                global memory_just_formed, curriculum_just_completed
                memory_just_formed = record_societal_memory(self.event_log, self.run_score())  # E29
                curriculum_just_completed = note_curriculum_run(self)  # E19
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
                    }
                )
                save_run_log_history(run_log_history)
                highest_awarded_run = self.run_number
                save_highest_awarded_run(highest_awarded_run)
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
        }


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
        localStorage.setItem(SKILL_TREE_STORAGE_KEY, json.dumps(self.to_dict()))

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
    localStorage.setItem(ACHIEVEMENT_PROGRESS_STORAGE_KEY, json.dumps(achievement_progress))


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
    localStorage.setItem(MENTOR_STORAGE_KEY, "1" if mentor_enabled else "0")
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


def render_past_runs_panel():
    toggle = document.getElementById("past-runs-toggle-button")
    panel = document.getElementById("past-runs-panel")
    toggle.innerText = "Hide Past Runs" if past_runs_open else f"📜 Review Past Runs ({len(run_log_history)})"
    panel.hidden = not past_runs_open
    if not past_runs_open:
        return

    panel.innerHTML = ""
    if not run_log_history:
        empty = document.createElement("p")
        empty.innerText = "No detailed run history yet — complete a run to start building one."
        panel.appendChild(empty)
        return

    record_indexes = new_record_run_indexes()
    for index in range(len(run_log_history) - 1, -1, -1):
        entry = run_log_history[index]
        card = document.createElement("div")
        is_record = index in record_indexes
        card.className = "past-run-card past-run-card--record" if is_record else "past-run-card"
        title = document.createElement("p")
        title.className = "past-run-title"
        title.innerText = (
            f"{'🏆 ' if is_record else ''}Run #{entry['run_number']} — score {entry['score']:.0f} "
            f"(resilience {entry['resilience_capacity']}, growth {entry['growth_capacity']}, "
            f"+{entry['knowledge_earned']} knowledge)"
        )
        card.appendChild(title)
        _render_event_breakdown_lines(card, entry["event_log"], show_category=True)
        panel.appendChild(card)


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
    severity = event_severity(run_state.run_number, run_state.event_index, skill_tree_strength())
    damage = EVENT_BASE_DAMAGE[event_type] * severity * (1 - run_state.mitigation_for(event_type))
    return damage, severity


def expected_damage_range(run_state):
    """E14: (low, high) damage for the next event across the whole
    severity band this settlement can face (min/max multiplier at the
    current skill level and career length). The center estimate above is
    exact for this run number; the range shows how much a different run
    number could swing the same event."""
    event_type = run_state.next_event_type()
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
def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
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
    localStorage.setItem(INVEST_STEP_STORAGE_KEY, str(value))
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


def announce(text):
    element = document.getElementById("event-announcer")
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


# ---- E-17: schedule strip -------------------------------------------------
def schedule_strip_entries(run_state):
    """One entry per event in the run's schedule: what it is, whether it is
    done / next / upcoming, and the numbers to show. Upcoming damage is exact
    for this run number (severity is deterministic) at the CURRENT build, so
    it moves as the player invests."""
    strength = skill_tree_strength()
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
            "category_bonus": category_mitigation_bonus(event_type),
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
            severity = event_severity(run_state.run_number, index, strength)
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
    document.getElementById("curriculum-display").innerText = curriculum_message()
    document.getElementById("resources-display").innerText = f"Resources: {run.resources:.0f}"
    document.getElementById("resilience-display").innerText = f"Resilience: {run.resilience_capacity}"
    document.getElementById("growth-display").innerText = (
        f"Growth: {run.growth_capacity} (+{growth_income_now(run.growth_capacity)} resources/event)"
    )
    document.getElementById("runs-completed-display").innerText = runs_completed_text()  # E4/E25
    document.getElementById("settlement-badge-toughest").classList.remove("settlement-badge--earned")
    if toughest_survived_run_badge_earned():  # E12
        document.getElementById("settlement-badge-toughest").classList.add("settlement-badge--earned")
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
            f"Total damage taken: {run.damage_taken:.0f}"
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
        run_summary_panel.appendChild(breakdown)
        epilogue = extended_epilogue_text(run)
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
        expected_el.title = severity_tooltip_text(run.run_number)
        document.getElementById("flawless-hint-display").innerText = flawless_hint_text(run)  # GE-15

        # E20: a live preview of the knowledge points a run would award
        # if it ended right now.
        knowledge_now = run.knowledge_points_earned()
        preview_el = document.getElementById("knowledge-preview-display")
        preview_el.innerText = (
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
    document.getElementById("extended-run-toggle-wrapper").hidden = not run.is_complete()
    # E17a: the scenario can be picked before a run's first event or between runs.
    document.getElementById("scenario-wrapper").hidden = not (run.is_complete() or run.event_index == 0)
    scenario_select = document.getElementById("scenario-select")
    if run.event_index == 0 and not run.is_complete():
        scenario_select.value = run.scenario
    document.getElementById("scenario-blurb").innerText = SCENARIOS[
        scenario_select.value if scenario_select.value in SCENARIOS else run.scenario
    ]["blurb"]
    document.getElementById("progress-comparison-display").innerText = progress_message(
        progress_comparison()
    )

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


def on_resolve_event(event=None):
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
    if value in SCENARIOS and run.event_index == 0 and not run.is_complete():
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
    global run, callout_message, last_knowledge_preview
    callout_message = ""
    last_knowledge_preview = None
    document.getElementById("copy-run-summary-status").innerText = ""
    document.getElementById("copy-run-summary-area").hidden = True
    announce("")
    extended = document.getElementById("extended-run-toggle").checked
    scenario = document.getElementById("scenario-select").value
    run = RunState(run_number=max(run.run_number, highest_awarded_run) + 1, extended=extended, scenario=scenario)
    render()
    _check_new_achievements_for_toast()


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
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back by load_state() below.
        "achievements_earned": achievement_ids_earned(),
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
    run = RunState(
        run_number=data["run_number"], extended=data.get("extended", False),
        scenario=saved_scenario if isinstance(saved_scenario, str) else DEFAULT_SCENARIO,
    )
    run.event_index = data["event_index"]
    run.resources = data["resources"]
    run.resilience_capacity = data["resilience_capacity"]
    run.growth_capacity = data["growth_capacity"]
    run.damage_taken = data["damage_taken"]
    run.event_log = copy.deepcopy(data["event_log"])
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


def _make_unlock_handler(skill_id):
    def handler(event=None):
        unlocked = skill_tree.unlock(skill_id)
        render()
        if unlocked:
            _display_skill_unlock_toast(skill_id)
        _check_new_achievements_for_toast()
    return handler


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
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("skill-unlock-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
