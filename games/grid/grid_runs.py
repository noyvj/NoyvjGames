"""Finishing and recording runs: starting a new run, finish_run, daily run, ghost traces and the run record.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import grid_runstate as runstate
from grid_rules import CAREER_HISTORY_MAX, CAREER_MIN_ROUNDS, CAREER_SERIES_POINTS, PLANT_TYPES, SEED_GAME
from grid_state import GridState
from grid_whatif import what_if_results
from grid_career_data import _sync_perks, run_ghost_traces, save_career_to_storage
from grid_career_actions import _add_to_lifetime, run_career_points
from grid_achievements import ACHIEVEMENTS, achievement_ids_earned
from grid_trend import ghost_record
from grid_announce import _seed_achievement_toast_baseline


def finish_run():
    """Bank this run into the career and start a fresh run. Returns the
    points banked, or None if the run is too short to count (nothing
    changes in that case)."""
    if runstate.sandbox_active:  # Z-18: a sandbox run never counts towards the career
        return None
    points, _ = run_career_points()
    if points <= 0 and runstate.state.round_number - 1 < CAREER_MIN_ROUNDS:
        return None
    grade = runstate.state.benchmark_grade() or "F"
    record = run_record(points, grade)
    broken = []
    first_run = runstate.career["runs"] == 0
    runstate.career["runs"] += 1
    runstate.career["points"] += points
    score = round(runstate.state.score(), 1)
    if score > runstate.career["best_score"]:
        if not first_run:
            broken.append(f"best clean score {score:.0f}/100")
        runstate.career["best_score"] = score
    order = "ABCDF"
    best = runstate.career["best_grade"]
    if best is None or order.index(grade) < order.index(best):
        if best is not None:
            broken.append(f"best operator grade {grade}")
        runstate.career["best_grade"] = grade
    if record["streak"] > runstate.career["best_streak"]:
        if not first_run:
            broken.append(f"longest disruption-free streak {record['streak']} rounds")
        runstate.career["best_streak"] = record["streak"]
    r90 = record["r90"]
    if r90 is not None and (runstate.career["best_rounds_to_90"] is None or r90 < runstate.career["best_rounds_to_90"]):
        if runstate.career["best_rounds_to_90"] is not None:
            broken.append(f"fewest rounds to 90% clean: {r90}")
        runstate.career["best_rounds_to_90"] = r90
    banked = set(runstate.career["achievements"]) | set(achievement_ids_earned())
    runstate.career["achievements"] = [e["id"] for e in ACHIEVEMENTS if e["id"] in banked]
    previous_ghost = ghost_record()
    runstate.career["history"] = (runstate.career["history"] + [record])[-CAREER_HISTORY_MAX:]
    _file_run_ghost(record, previous_ghost)
    _add_to_lifetime(record)
    runstate.last_finish_records = broken
    save_career_to_storage()
    _record_shared_daily(runstate.state.seed, grade, score)
    _start_new_run()
    return points


def _record_shared_daily(seed_text, grade, score):
    """Z-5c: a finished run whose seed is TODAY's shared seed counts once for the day in the record the hub's Today strip
    reads (`localStorage["noyvj-daily-v1"]`, written by `NoyvjSeed.daily.markCompleted`). The page decides what today is
    (`isDaily`), so a run begun on an older day's seed, or any ordinary run, records nothing. Fails soft: no shared script
    (pytest, an old page) or any error means nothing, and the run's own result is never affected."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        daily = getattr(getattr(js.window, "NoyvjSeed", None), "daily", None)
        if daily is None or not daily.isDaily(SEED_GAME, seed_text):
            return
        info = js.Object.new()
        info.text = f"Grade {grade}, clean score {score:.0f} of 100"
        daily.markCompleted(SEED_GAME, info)
    except Exception:  # noqa: BLE001 -- a courtesy record must never break finishing a run
        pass


def _tell_footer_seed():
    """Put the run's own seed back in the info footer (the shared button shows today's seed the moment it is pressed)."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        seed_api = getattr(js.window, "NoyvjSeed", None)
        if seed_api is not None:
            seed_api.set(runstate.state.seed)
    except Exception:  # noqa: BLE001 -- the footer's seed line is a courtesy
        pass


def _thin(values, scale=1.0):
    """C-1: at most CAREER_SERIES_POINTS evenly spaced, rounded points."""
    n = len(values)
    if n == 0:
        return []
    if n > CAREER_SERIES_POINTS:
        idx = [round(i * (n - 1) / (CAREER_SERIES_POINTS - 1)) for i in range(CAREER_SERIES_POINTS)]
        values = [values[i] for i in idx]
    return [int(round(v * scale)) for v in values]


def _file_run_ghost(record, previous):
    """Z-3c: keep this run's trace as the best-run ghost when it scores at least as well as the ghost it
    would replace (the latest wins a tie, as before). Called with the run just filed in the history."""
    if record["rounds"] < 2 or (previous is not None and record["score"] < previous["score"]):
        return
    label = _run_label(runstate.career["history"], len(runstate.career["history"]) - 1)
    traces = run_ghost_traces(runstate.state.clean_fraction_log, runstate.state.funds_history, label)
    if traces is None:
        return
    runstate.career["ghost"] = {"label": label, "grade": record["grade"], "score": record["score"],
                       "clean": traces["clean"], "funds": traces["funds"]}


def run_record(points, grade):
    """C-1: the current run, filed as one history record (what the Career
    panel's history list, stacked charts and lifetime statistics read)."""
    brownouts = sum(1 for e in runstate.state.event_log if e.get("type") == "brownout")
    damages = sum(1 for e in runstate.state.event_log if e.get("type") == "damage")
    return {
        "scenario": runstate.state.scenario,
        "grade": grade,
        "points": points,
        "rounds": runstate.state.round_number - 1,
        "score": round(runstate.state.score(), 1),
        "resilience": runstate.state.resilience_score(),
        "funds": max(0, int(round(runstate.state.funds))),
        "emissions": max(0, int(round(runstate.state.emissions))),
        "streak": runstate.state.best_clean_streak,
        "brownouts": brownouts,
        "damages": damages,
        "aging": runstate.state.aging_breakdown_count,
        "r90": runstate.state.first_90_clean_round,
        "built": {t: runstate.state.cumulative_built.get(t, 0) for t in PLANT_TYPES},
        "clean": _thin(runstate.state.clean_fraction_log, 100.0),
        "funds_series": _thin([max(0, v) for v in runstate.state.funds_history]),
        "demand_series": _thin(runstate.state.demand_history),
        "seed": runstate.state.seed,
        "ironman": runstate.state.ironman,
        "whatif": what_if_results(runstate.state),
    }


def _start_new_run():
    """C1: replace the live GridState with a fresh one carrying the
    career's unlocked perks (seed capital is applied via the standard
    scenario so it uses the same funds path as every other start)."""
    runstate.state = GridState()
    _sync_perks()
    runstate.state.start_option = runstate.career["loadout"]
    runstate.state.apply_scenario("standard")
    runstate.renewable_milestone_visible = False
    runstate.retire_callout_visible = False
    runstate.maintain_callout_visible = False
    _seed_achievement_toast_baseline()


def _run_label(history, index):
    return f"Run {max(0, runstate.career['runs'] - len(history)) + index + 1}"
