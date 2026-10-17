"""What skills and the second founding add to a run, societal memory, mutual aid from neighbouring towns (R-31), settlement looks and the run-timer helpers."""

import json
import math

from js import localStorage

import aftermath_runstate as runstate
from aftermath_persist import (
    FOUNDING_CATEGORY_BONUS, FOUNDING_SILENCES, FOUNDING_START_GROWTH, FOUNDING_START_RESOURCES,
    FOUNDING_STAR_RESOURCES, SOCIETAL_MEMORY_BONUS, VERY_BAD_RUN_SCORE, _el, _now, run_log_history,
    save_societal_memory, societal_memory,
)
from aftermath_rules import EVENT_CATEGORY, EVENT_LABEL, GROWTH_COST, GROWTH_INCOME_PER_UNIT, SKILLS


# E-4: every helper below reads the skill tree through an optional `unlocked`
# argument, so a challenge run (which ignores the player's tree) can pass an
# empty set instead of switching on global state.
def founding_owned():
    """GE-10: the Founding skills held (empty without a star)."""
    founding = runstate.meta["founding"]
    return frozenset(founding["owned"]) if founding["stars"] >= 1 else frozenset()


def _unlocked_or_tree(unlocked):
    """The skills in force: the ones passed in (a challenge run passes none), else the player's tree plus any
    Founding skills (GE-10). Every bonus helper below reads skills through this, so a Founding skill is just
    one more id they know about."""
    return (runstate.skill_tree.unlocked | founding_owned()) if unlocked is None else unlocked


def founding_star_resources():
    """GE-10: the permanent starting-resources perk of the Founding stars."""
    return runstate.meta["founding"]["stars"] * FOUNDING_STAR_RESOURCES


def starting_resources_bonus(unlocked=None):
    tree = _unlocked_or_tree(unlocked)
    bonus = 50 if "community_reserves" in tree else 0
    return bonus + sum(amount for skill_id, amount in FOUNDING_START_RESOURCES.items() if skill_id in tree)


def starting_resilience_bonus(unlocked=None):
    return 2 if "reinforced_infrastructure" in _unlocked_or_tree(unlocked) else 0


def founding_silenced(unlocked=None):
    """GE-10: the skills a held Founding skill switches off (Frontier Charter silences Early Warning Systems and
    Mutual Aid Network): they stay owned but add no mitigation."""
    tree = _unlocked_or_tree(unlocked)
    return {silenced for skill_id, targets in FOUNDING_SILENCES.items() if skill_id in tree for silenced in targets}


def early_warning_mitigation_bonus(unlocked=None):
    tree = _unlocked_or_tree(unlocked)
    return 0.10 if "early_warning" in tree and "early_warning" not in founding_silenced(tree) else 0.0


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
    tree = _unlocked_or_tree(unlocked)
    return (1 if "adaptive_growth" in tree else 0) + sum(amount for skill_id, amount in FOUNDING_START_GROWTH.items() if skill_id in tree)


def mutual_aid_mitigation_bonus(unlocked=None):
    """E2: the fifth skill node -- flat mitigation like early_warning's,
    but gated behind E3's prereq structure (both foundational skills)."""
    tree = _unlocked_or_tree(unlocked)
    return 0.05 if "mutual_aid_network" in tree and "mutual_aid_network" not in founding_silenced(tree) else 0.0


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
    ) + sum(amount for skill_id, cat, amount in FOUNDING_CATEGORY_BONUS if cat == category and skill_id in tree)  # GE-10


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


# ---------------------------------------------------------------------------
# R-31: mutual aid from neighbouring towns (opt-in, default OFF). When the community's AVERAGE tree
# strength (the write-only `skill_tree_strength` every save carries, aggregated by the backend at
# GET /stats/games/aftermath) reaches NEIGHBOUR_AID_MIN_COMMUNITY_STRENGTH, a player who switched this on in
# Settings gets ONE gentle gift per run: "+N resources" just before one fixed event. Nothing here is luck:
#   * which event and how many resources come only from the run number (aid_hash), so the same run
#     always gets the same help and the page shows it BEFORE the run starts;
#   * with the setting off, with no community figure (offline, too few players, a backend that does not
#     list the field, or "reduce data" with nothing cached) or below the threshold, nothing happens;
#   * challenge runs (a friend's run code) and built schedules never get aid;
#   * a run that received aid is TAGGED (`aid` on the event, `neighbour_aid` in its log entry): it never
#     reaches the hardest-schedule board, is not a Past Runs record, does not earn the "toughest run
#     survived" badge and gets no shareable run code. No achievement needs aid (all stay reachable
#     without it), and the aid itself only counts as resources in that run.
# ---------------------------------------------------------------------------
NEIGHBOUR_AID_STORAGE_KEY = "aftermath-neighbour-aid"  # the Settings switch ("true" = on); settings.js writes it
COMMUNITY_RESILIENCE_CACHE_KEY = "aftermath_community_resilience_v1"  # last community mean, so a reload or offline visit agrees
COMMUNITY_RESILIENCE_CACHE_DAYS = 14
NEIGHBOUR_AID_MIN_COMMUNITY_STRENGTH = 3.0  # community mean skills unlocked (of the 7 in the tree)
NEIGHBOUR_AID_AMOUNTS = (15, 20, 25)  # resources; roughly one investment unit, so gentle next to 200 starting


def entry_aid(entry):
    """Resources a logged event received from neighbouring towns (0 unless it is a real positive number:
    a damaged save value counts as none)."""
    value = entry.get("aid") if isinstance(entry, dict) else None
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0
    return value if ok else 0


def neighbour_aid_enabled():
    try:
        return localStorage.getItem(NEIGHBOUR_AID_STORAGE_KEY) == "true"
    except Exception:
        return False


def _community_value(mean):
    """A finite number from 0 to the number of skills, else None."""
    if isinstance(mean, bool) or not isinstance(mean, (int, float)):
        return None
    if not math.isfinite(mean) or not 0 <= mean <= len(SKILLS):
        return None
    return float(mean)


def load_cached_community_resilience():
    """Reads the last community mean this browser fetched (at most COMMUNITY_RESILIENCE_CACHE_DAYS old).
    Returns True when a figure was restored."""
    try:
        data = json.loads(localStorage.getItem(COMMUNITY_RESILIENCE_CACHE_KEY) or "")
    except (ValueError, TypeError):
        return False
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    value = _community_value(data.get("mean"))
    stamp = data.get("at")
    if value is None or isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
        return False
    if _now() - stamp > COMMUNITY_RESILIENCE_CACHE_DAYS * 86400 or stamp > _now() + 86400:
        return False
    runstate.community_resilience = value
    return True


def community_aid_available():
    return runstate.community_resilience is not None and runstate.community_resilience >= NEIGHBOUR_AID_MIN_COMMUNITY_STRENGTH


def aid_hash(run_number):
    """A fixed scramble of the run number (never random): the same run number always gives the same value."""
    return ((int(run_number) * 2654435761) % 4294967296) >> 8


def neighbour_aid_schedule(run_number, schedule_length):
    """(event index, resources) for a run. The index is never the first or the last event, so the gift is
    neither a free opening nor a last-second rescue; the amount is one of NEIGHBOUR_AID_AMOUNTS."""
    h = aid_hash(run_number)
    span = max(1, schedule_length - 2)
    return 1 + h % span, NEIGHBOUR_AID_AMOUNTS[(h >> 8) % len(NEIGHBOUR_AID_AMOUNTS)]


def neighbour_aid_plan(run_state):
    """The aid still to come in this run as {"index", "amount", "event"}, or None: switched off, no
    (or too low a) community figure, a challenge or built-schedule run, aid already received, or the
    run's help point already behind it."""
    if not neighbour_aid_enabled() or not community_aid_available():
        return None
    if run_state.normalised or run_state.custom_events or run_state.aid_given:
        return None
    index, amount = neighbour_aid_schedule(run_state.run_number, len(run_state.schedule))
    if index < run_state.event_index:
        return None
    return {"index": index, "amount": amount, "event": run_state.schedule[index]}


def neighbour_aid_due(run_state):
    """Resources arriving with the event about to resolve (0 almost always)."""
    plan = neighbour_aid_plan(run_state)
    return plan["amount"] if plan is not None and plan["index"] == run_state.event_index else 0


def neighbour_aid_message(run_state=None):
    """The one line shown under the damage preview: what is planned, what arrived, or why nothing is coming.
    Empty while the setting is off."""
    run_state = run_state or runstate.run
    if not neighbour_aid_enabled():
        return ""
    if run_state.normalised or run_state.custom_events:
        return "Mutual aid does not apply to challenge runs or built schedules."
    if run_state.aid_given:
        number = next((i + 1 for i, e in enumerate(run_state.event_log) if entry_aid(e)), None)
        where = f" before event {number}" if number else ""
        return (
            f"Neighbouring towns sent help{where}: +{run_state.aid_given:.0f} resources. "
            "This run is marked, so it stays off the hardest-schedule board and gets no run code."
        )
    if runstate.community_resilience is None:
        return "Mutual aid is on, but the community figure is not available, so no help comes this run."
    if not community_aid_available():
        return (
            f"Mutual aid is on, but players' average resilience ({runstate.community_resilience:.1f} of {len(SKILLS)} skills) "
            f"is below the {NEIGHBOUR_AID_MIN_COMMUNITY_STRENGTH:.0f} needed, so no help comes this run."
        )
    plan = neighbour_aid_plan(run_state)
    if plan is None:
        return "Mutual aid is on, but this run's help point has passed, so no help comes this run."
    return (
        f"Neighbouring towns will send help before event {plan['index'] + 1} ({EVENT_LABEL[plan['event']]}): "
        f"+{plan['amount']} resources. Fixed by this run's number, never luck. "
        "It marks the run: off the boards, no run code."
    )


def render_neighbour_aid():
    el = _el("neighbour-aid-display")
    if el is None:
        return
    text = neighbour_aid_message()
    el.innerText = text
    el.hidden = not text


# ---------------------------------------------------------------------------
# GE-25: settlement looks. The settlement is drawn as thatched huts, timber halls or concrete and glass,
# by how many of the tree's skills are owned when a run starts (thresholds come from the tree's real
# size: half of it, rounded up, and all of it). A look is only art and a collectible: it changes no
# number. The look rides the run's history entry (only when it is not the default) so Past Runs can say
# which look each run had, and "looks seen" is read from that history.
# ---------------------------------------------------------------------------
SETTLEMENT_LOOKS = (
    ("thatched", "Thatched huts"),
    ("timber", "Timber halls"),
    ("concrete", "Concrete and glass"),
)
DEFAULT_LOOK = "thatched"
_LOOK_LABELS = dict(SETTLEMENT_LOOKS)


def look_thresholds(skill_count=None):
    """Skills needed for each look: none, half the tree (rounded up) and the whole tree."""
    total = len(SKILLS) if skill_count is None else skill_count
    return {"thatched": 0, "timber": max(1, (total + 1) // 2), "concrete": max(2, total)}


def look_for_skill_count(count):
    thresholds = look_thresholds()
    best = DEFAULT_LOOK
    for key, _label in SETTLEMENT_LOOKS:
        if count >= thresholds[key]:
            best = key
    return best


def look_label(key):
    return _LOOK_LABELS.get(key, _LOOK_LABELS[DEFAULT_LOOK])


def entry_look(entry):
    """The look a logged run had; anything missing or unknown reads as the default."""
    value = entry.get("look") if isinstance(entry, dict) else None
    return value if isinstance(value, str) and value in _LOOK_LABELS else DEFAULT_LOOK


def looks_seen(run_state=None):
    """The looks this settlement has had in at least one run (the default always counts)."""
    seen = {DEFAULT_LOOK}
    seen.update(entry_look(e) for e in run_log_history)
    if run_state is not None:
        seen.add(getattr(run_state, "look", DEFAULT_LOOK))
    return seen


# ---------------------------------------------------------------------------
# GE-23: the optional run timer. OFF by default (Settings). When on, the time from a run's first action to its
# last event is shown while playing, kept on the run's history entry as "seconds" and listed in Past Runs
# (with a "fastest" mark and a Fastest finish sort). Time never touches a score, knowledge, an achievement or a
# board. Only time spent with the page in front counts (each step adds at most TIMER_MAX_STEP seconds).
# ---------------------------------------------------------------------------
RUN_TIMER_STORAGE_KEY = "aftermath-run-timer"  # settings.js writes "true" or "false"; missing = off
TIMER_MAX_STEP = 5.0
TIMER_MAX_SECONDS = 24 * 60 * 60


def run_timer_enabled():
    try:
        return localStorage.getItem(RUN_TIMER_STORAGE_KEY) == "true"
    except Exception:
        return False


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def entry_seconds(entry):
    """The timed finish of a logged run in whole seconds, or None (no timer, or a damaged value)."""
    value = entry.get("seconds") if isinstance(entry, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= TIMER_MAX_SECONDS:
        return None
    return int(value)


def fastest_run_number():
    """The run number with the shortest timed finish (the earliest one on a tie), or None when no run was timed."""
    best, best_number = None, None
    for entry in run_log_history:
        seconds = entry_seconds(entry)
        if seconds is not None and isinstance(entry, dict) and (best is None or seconds < best):
            best, best_number = seconds, entry.get("run_number")
    return best_number
