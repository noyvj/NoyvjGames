"""Career actions: career points for a run, adding to lifetime totals, unlocking perks, choosing a loadout.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import skill_tree

import grid_runstate as runstate
from grid_rules import (
    CAREER_GRADE_POINTS, CAREER_MIN_ROUNDS, CAREER_RESILIENCE_BONUS_THRESHOLD, CAREER_TREE, LOADOUT_NODES,
    PLANT_TYPES,
)
from grid_career_data import _sync_perks, save_career_to_storage


def run_career_points():
    """Points finishing the current run would bank, with a short breakdown
    list; (0, [reason]) if the run is too short to count."""
    rounds_played = runstate.state.round_number - 1
    if rounds_played < CAREER_MIN_ROUNDS:
        return 0, [f"Play at least {CAREER_MIN_ROUNDS} rounds ({rounds_played} so far) for a run to count."]
    grade = runstate.state.benchmark_grade() or "F"
    parts = ["1 for finishing", f"{CAREER_GRADE_POINTS[grade]} for operator grade {grade}"]
    total = 1 + CAREER_GRADE_POINTS[grade]
    if runstate.state.resilience_score() >= CAREER_RESILIENCE_BONUS_THRESHOLD:
        total += 1
        parts.append("1 for resilience 60+")
    if runstate.state.emergency is not None and runstate.state.emergency["status"] == "stabilized":
        total += 1
        parts.append("1 for stabilizing the emergency")
    return total, parts


def _add_to_lifetime(record):
    life = runstate.career["lifetime"]
    life["rounds"] += record["rounds"]
    for t in PLANT_TYPES:
        life["built"][t] += record["built"][t]
    life["brownouts"] += record["brownouts"]
    life["damages"] += record["damages"]
    life["aging"] += record["aging"]
    entry = life["scenario_grades"].setdefault(record["scenario"], {"n": 0, "points": 0})
    entry["n"] += 1
    entry["points"] += CAREER_GRADE_POINTS[record["grade"]]


def unlock_career_perk(perk_id):
    """Buy one node of the upgrade tree with career points (prerequisites must be owned)."""
    if runstate.sandbox_active:  # Z-18: everything is already on, and the career is not touched
        return False
    result = skill_tree.buy(CAREER_TREE, runstate.career["unlocked"], perk_id, runstate.career["points"])
    if not result["ok"]:
        return False
    runstate.career["unlocked"] = result["owned"]
    save_career_to_storage()
    _refresh_unstarted_run()
    return True


def _refresh_unstarted_run():
    """A run that has not started yet picks up newly bought nodes at once (seed money, a loadout
    choice); a run in progress keeps its rules until the next run, as before."""
    if runstate.state.unstarted():
        _sync_perks()
        if runstate.state.start_option not in runstate.state.perks:
            runstate.state.start_option = None
        runstate.state.apply_scenario(runstate.state.scenario)


def set_loadout(option):
    """GC-2b: choose the starting loadout for this run and the next ones (None = no loadout)."""
    if runstate.sandbox_active:  # Z-18: any loadout may be tried; the career's chosen loadout is not touched
        if option is not None and option not in LOADOUT_NODES:
            return False
        if runstate.state.unstarted():
            runstate.state.start_option = option
            runstate.state.apply_scenario(runstate.state.scenario)
        return True
    if option is not None and option not in runstate.career["unlocked"]:
        return False
    if option is not None and option not in LOADOUT_NODES:
        return False
    runstate.career["loadout"] = option
    save_career_to_storage()
    if runstate.state.unstarted():
        _sync_perks()
        runstate.state.start_option = option
        runstate.state.apply_scenario(runstate.state.scenario)
    return True
