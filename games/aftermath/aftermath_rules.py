"""Fixed numbers and content tables: costs, the event schedule and scenarios, event labels and damage, severity helpers, the skill catalog and storage keys. No browser calls, no state."""

import aftermath_runstate as runstate


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


# E7: a proper difficulty-scaling curve across many runs -- beyond the
# per-skill widening above, the severity spread also grows slowly with the
# number of runs the player has completed over the settlement's lifetime,
# capped so a very long career can't run away. The center stays 1.0, same
# hope-angle reasoning as SEVERITY_VARIATION_RANGE_PER_SKILL.
SEVERITY_VARIATION_RANGE_PER_LIFETIME_RUN = 0.004
SEVERITY_LIFETIME_RANGE_CAP = 0.06


def lifetime_severity_widening(lifetime_runs=None):
    if lifetime_runs is None:
        lifetime_runs = len(runstate.run_history)
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
