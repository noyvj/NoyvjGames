"""Achievements: the checks, progress readouts, milestone text and the earned list.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

import grid_runstate as runstate
from grid_rules import MIN_COST_MULTIPLIER, PLANT_BASE_COST, PLANT_CAPACITY, PLANT_TYPES, RENEWABLE_TYPES


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration (games/sol/game.py). Every achievement's earned status is a
# pure function of state that already exists elsewhere in this module,
# recomputed fresh every call — never a separately hand-maintained "earned"
# flag. Three exceptions needed genuinely new tracked state (declared on
# GridState above, mutated only where the real event happens: a successful
# maintain_plant() call, or a round advancing with/without a disruption
# event) — nothing else in this module records how many times Maintain has
# been used, or how long a streak of disruption-free rounds has run.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()` / Le
    Champ de Mots' `_read_json_asset()`: the boot script fetches
    achievements.json and hands it to Python as a window global before this
    file runs; the pytest harness's fake `js` module has no such attribute,
    so this falls through to reading the file straight off disk, keeping
    the module importable outside a real browser."""
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
# whole import — achievements are additive, not core to Grid's gameplay
# (same posture SOL/Le Champ de Mots take for their own optional assets).
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

MAINTENANCE_ACHIEVEMENT_TARGET = 5
CLEAN_STREAK_TARGET = 15
NO_DAMAGE_ROUND_TARGET = 21
SCORE_50_MIN_ROUNDS = 10
SCORE_80_MIN_ROUNDS = 20
AHEAD_OF_CURVE_MIN_ROUND = 11
GRID_AT_SCALE_TARGET = 300


def renewable_capacity_share():
    """Renewables' share of total standing capacity, 0..1. Shared by the
    achievements below and (later) the one-time 50%-crossing callout."""
    total = runstate.state.total_capacity()
    if total == 0:
        return 0.0
    renewable_capacity = sum(runstate.state.plant_counts[t] * PLANT_CAPACITY[t] for t in RENEWABLE_TYPES)
    return renewable_capacity / total


def _standing_plant_type_count():
    return sum(1 for t in PLANT_TYPES if runstate.state.plant_counts[t] >= 1)


def _any_renewable_at_cost_floor():
    return any(
        runstate.state.plant_cost(t) <= PLANT_BASE_COST[t] * MIN_COST_MULTIPLIER * 1.0001
        for t in RENEWABLE_TYPES
    )


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_watt": lambda: sum(runstate.state.plant_counts.values()) >= 1,
    "renewable_pioneer": lambda: any(runstate.state.plant_counts[t] >= 1 for t in RENEWABLE_TYPES),
    "first_storage": lambda: runstate.state.cumulative_built["battery"] >= 1,
    "clean_quarter": lambda: renewable_capacity_share() >= 0.25,
    "clean_half": lambda: renewable_capacity_share() >= 0.5,
    "clean_three_quarters": lambda: renewable_capacity_share() >= 0.75,
    "fully_renewable": lambda: runstate.state.total_capacity() > 0 and runstate.state.fossil_share() == 0.0,
    "learning_curve_floored": _any_renewable_at_cost_floor,
    "diverse_grid": lambda: _standing_plant_type_count() >= len(PLANT_TYPES),
    "fossil_phase_out": lambda: (
        runstate.state.cumulative_built["coal"] + runstate.state.cumulative_built["gas"] >= 3
        and runstate.state.plant_counts["coal"] == 0
        and runstate.state.plant_counts["gas"] == 0
        and runstate.state.total_capacity() > 0
    ),
    "clean_streak_15": lambda: runstate.state.best_clean_streak >= CLEAN_STREAK_TARGET,
    "no_damage_20": lambda: (
        runstate.state.round_number >= NO_DAMAGE_ROUND_TARGET
        and not any(e.get("type") == "damage" for e in runstate.state.event_log)
    ),
    "score_50": lambda: runstate.state.score() >= 50 and len(runstate.state.clean_fraction_log) >= SCORE_50_MIN_ROUNDS,
    "score_80": lambda: runstate.state.score() >= 80 and len(runstate.state.clean_fraction_log) >= SCORE_80_MIN_ROUNDS,
    "well_maintained": lambda: runstate.state.maintenance_actions_count >= MAINTENANCE_ACHIEVEMENT_TARGET,
    "ahead_of_the_curve": lambda: (
        runstate.state.round_number >= AHEAD_OF_CURVE_MIN_ROUND
        and runstate.state.emissions < runstate.state.global_reference_emissions
    ),
    "grid_at_scale": lambda: runstate.state.total_capacity() >= GRID_AT_SCALE_TARGET,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "retire every fossil plant you built".
ACHIEVEMENT_PROGRESS = {
    "clean_quarter": lambda: (min(100, round(renewable_capacity_share() * 100)), 25),
    "clean_half": lambda: (min(100, round(renewable_capacity_share() * 100)), 50),
    "clean_three_quarters": lambda: (min(100, round(renewable_capacity_share() * 100)), 75),
    "diverse_grid": lambda: (_standing_plant_type_count(), len(PLANT_TYPES)),
    "clean_streak_15": lambda: (min(runstate.state.best_clean_streak, CLEAN_STREAK_TARGET), CLEAN_STREAK_TARGET),
    "score_50": lambda: (min(100, round(runstate.state.score())), 50),
    "score_80": lambda: (min(100, round(runstate.state.score())), 80),
    "well_maintained": lambda: (
        min(runstate.state.maintenance_actions_count, MAINTENANCE_ACHIEVEMENT_TARGET),
        MAINTENANCE_ACHIEVEMENT_TARGET,
    ),
    "grid_at_scale": lambda: (min(runstate.state.total_capacity(), GRID_AT_SCALE_TARGET), GRID_AT_SCALE_TARGET),
    # C-18: the remaining countable ones.
    "fully_renewable": lambda: _progress_fully_renewable(),
    "learning_curve_floored": lambda: _progress_learning_curve(),
    "fossil_phase_out": lambda: _progress_fossil_phase_out(),
    "no_damage_20": lambda: _progress_no_damage(),
    "ahead_of_the_curve": lambda: _progress_ahead_of_curve(),
}


def _progress_fully_renewable():
    """Share of standing capacity that is not coal or gas, out of 100 (nothing standing reads 0)."""
    if runstate.state.total_capacity() <= 0:
        return (0, 100)
    return (min(100, int(round((1 - runstate.state.fossil_share()) * 100))), 100)


def _progress_learning_curve():
    """How far the most-built renewable type has come down the learning curve towards its price floor, as a
    percentage of the whole way (100 = at the floor). Reads the learning-curve price, never a policy discount."""
    best = 0.0
    for plant_type in RENEWABLE_TYPES:
        multiplier = runstate.state._learning_curve_cost(plant_type) / PLANT_BASE_COST[plant_type]
        best = max(best, (1 - multiplier) / (1 - MIN_COST_MULTIPLIER))
    return (max(0, min(100, int(round(best * 100)))), 100)


def _progress_fossil_phase_out():
    """First build three fossil plants (counted as built, ever); then the count is how many of those fossil units
    have been retired so far, out of all that were built."""
    built = runstate.state.cumulative_built["coal"] + runstate.state.cumulative_built["gas"]
    if built < 3:
        return (built, 3)
    standing = runstate.state.plant_counts["coal"] + runstate.state.plant_counts["gas"]
    return (max(0, min(built, built - standing)), built)


def _progress_no_damage():
    """Rounds reached out of 21 while no plant has been damaged; None once one has (the run can no longer earn it)."""
    if any(e.get("type") == "damage" for e in runstate.state.event_log):
        return None
    return (min(runstate.state.round_number, NO_DAMAGE_ROUND_TARGET), NO_DAMAGE_ROUND_TARGET)


def _progress_ahead_of_curve():
    """Rounds reached out of 11; after that the question is whether emissions are below the benchmark, which is not
    a count, so there is no readout."""
    if runstate.state.round_number >= AHEAD_OF_CURVE_MIN_ROUND:
        return None
    return (runstate.state.round_number, AHEAD_OF_CURVE_MIN_ROUND)


def next_milestone():
    """C-18: the locked achievement that is furthest along (largest fraction of its readout, below the whole), as
    its summary entry, or None when none has a readout in progress."""
    best = None
    best_fraction = -1.0
    for entry in achievements_summary():
        if entry["earned"] or entry["progress"] is None:
            continue
        current, target = entry["progress"]
        if target <= 0 or current >= target:
            continue
        fraction = current / target
        if current > 0 and fraction > best_fraction:
            best, best_fraction = entry, fraction
    return best


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    if runstate.sandbox_active:  # Z-18: nothing in the sandbox earns anything; the real game's list is shown as it was
        return list(runstate._sandbox_real["earned"])
    banked = set(runstate.career["achievements"])
    return [entry["id"] for entry in ACHIEVEMENTS if entry["id"] in banked or ACHIEVEMENT_CHECKS[entry["id"]]()]


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


# ---- C-31 achievement cards in the skyline look ---------------------------------------------------------------------
# Each achievement is a little building from the city skyline (the shape depends on its place in the list). Earned: a lit
# building with windows. Not earned: the same building as a dark outline with no windows, so the state is shape and words
# as well as colour. A card earned since the panel was last drawn also gets a one-off "power up" flash (windows switch
# on in turn) and the words "Just powered up"; the flash is off under reduced motion and with the Settings checkbox.
_achievement_powerup_ids = set()
