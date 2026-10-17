"""The Grid Operator career record (C1): defaults, validation of saved careers, ghost traces and browser storage.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

import ghost as ghost_lib
import seed as seed_lib
import skill_tree

import grid_runstate as runstate
from grid_rules import (
    CAREER_GRADE_POINTS, CAREER_HISTORY_MAX, CAREER_SERIES_POINTS, CAREER_STORAGE_KEY, CAREER_TREE,
    LOADOUT_NODES, PLANT_TYPES, SCENARIOS, SEED_GAME,
)
from grid_sandbox_state import SANDBOX_ALL_PERKS
from grid_whatif import WHATIF_STRATEGIES


# --- C1: grid operator career ------------------------------------------------
# Persisted in the browser's localStorage (survives across runs, unlike the
# per-run save code) and mirrored into get_state() so a save code carries it
# to another device; load_state() only adopts a saved career that has
# completed at least as many runs as the live one (never rolls it back).

def _default_lifetime():
    return {
        "rounds": 0,
        "built": {t: 0 for t in PLANT_TYPES},
        "brownouts": 0,
        "damages": 0,
        "aging": 0,
        "scenario_grades": {},
    }


def _default_career():
    return {
        "runs": 0,
        "points": 0,
        "best_score": 0.0,
        "best_grade": None,
        "unlocked": [],
        "achievements": [],
        # C-1: the last CAREER_HISTORY_MAX finished runs (oldest first).
        "history": [],
        # C-7: uncapped lifetime totals behind the lifetime statistics.
        "lifetime": _default_lifetime(),
        # GC-26: personal records (None = not set yet).
        "best_streak": 0,
        "best_rounds_to_90": None,
        # GC-2b: the starting loadout chosen for the next run (None = none).
        "loadout": None,
    }


def _career_number(value, default, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    return max(lo, min(hi, value))


def _clean_series(raw, lo, hi):
    """C-1: a saved per-round series -> a list of at most
    CAREER_SERIES_POINTS finite numbers clamped into [lo, hi]."""
    if not isinstance(raw, list):
        return []
    out = []
    for value in raw[:CAREER_SERIES_POINTS]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            return []
        out.append(max(lo, min(hi, int(round(value)))))
    return out


def _clean_seed(raw):
    if not isinstance(raw, str):
        return ""
    return seed_lib.normalize(raw, SEED_GAME)


def _validate_whatif(raw):
    """C-3: the saved what-if rows -> at most one row per known strategy."""
    out = []
    if not isinstance(raw, list):
        return out
    known = {key for key, _label in WHATIF_STRATEGIES}
    for entry in raw:
        if not isinstance(entry, dict) or entry.get("id") not in known or entry["id"] in [o["id"] for o in out]:
            continue
        grade = entry.get("grade")
        out.append({
            "id": entry["id"],
            "grade": grade if grade in CAREER_GRADE_POINTS else "F",
            "funds": int(_career_number(entry.get("funds"), 0, 0, 10 ** 9)),
            "score": round(float(_career_number(entry.get("score"), 0.0, 0.0, 100.0)), 1),
        })
    return out


def _validate_run_record(raw):
    """C-1: one finished-run record, or None if it is not usable."""
    if not isinstance(raw, dict):
        return None
    scenario = raw.get("scenario")
    grade = raw.get("grade")
    if scenario not in SCENARIOS or grade not in CAREER_GRADE_POINTS:
        return None
    built = raw.get("built") if isinstance(raw.get("built"), dict) else {}
    r90 = raw.get("r90")
    return {
        "scenario": scenario,
        "grade": grade,
        "points": int(_career_number(raw.get("points"), 0, 0, 100)),
        "rounds": int(_career_number(raw.get("rounds"), 0, 0, 100000)),
        "score": round(float(_career_number(raw.get("score"), 0.0, 0.0, 100.0)), 1),
        "resilience": int(_career_number(raw.get("resilience"), 0, 0, 100)),
        "funds": int(_career_number(raw.get("funds"), 0, 0, 10 ** 9)),
        "emissions": int(_career_number(raw.get("emissions"), 0, 0, 10 ** 9)),
        "streak": int(_career_number(raw.get("streak"), 0, 0, 100000)),
        "brownouts": int(_career_number(raw.get("brownouts"), 0, 0, 100000)),
        "damages": int(_career_number(raw.get("damages"), 0, 0, 100000)),
        "aging": int(_career_number(raw.get("aging"), 0, 0, 100000)),
        "r90": (
            int(_career_number(r90, 1, 1, 100000))
            if isinstance(r90, (int, float)) and not isinstance(r90, bool) and r90 == r90
            else None
        ),
        "built": {t: int(_career_number(built.get(t), 0, 0, 100000)) for t in PLANT_TYPES},
        "clean": _clean_series(raw.get("clean"), 0, 100),
        "funds_series": _clean_series(raw.get("funds_series"), 0, 10 ** 9),
        "demand_series": _clean_series(raw.get("demand_series"), 0, 10 ** 9),
        # 2026-10-08: the run's seed, whether it was Ironman, and the C-3 what-if results.
        "seed": _clean_seed(raw.get("seed")),
        "ironman": bool(raw.get("ironman", False)),
        "whatif": _validate_whatif(raw.get("whatif")),
    }


def _validate_lifetime(raw):
    out = _default_lifetime()
    if not isinstance(raw, dict):
        return out
    out["rounds"] = int(_career_number(raw.get("rounds"), 0, 0, 10 ** 7))
    built = raw.get("built") if isinstance(raw.get("built"), dict) else {}
    out["built"] = {t: int(_career_number(built.get(t), 0, 0, 10 ** 7)) for t in PLANT_TYPES}
    for key in ("brownouts", "damages", "aging"):
        out[key] = int(_career_number(raw.get(key), 0, 0, 10 ** 7))
    grades = raw.get("scenario_grades")
    if isinstance(grades, dict):
        for scenario, entry in grades.items():
            if scenario in SCENARIOS and isinstance(entry, dict):
                runs = int(_career_number(entry.get("n"), 0, 0, 100000))
                if runs > 0:
                    out["scenario_grades"][scenario] = {
                        "n": runs,
                        "points": int(_career_number(entry.get("points"), 0, 0, 100000 * 4)),
                    }
    return out


def _validate_career_ghost(raw):
    """Z-3c: the saved best-run ghost -> a clean dict, or None. Every field is checked; the two traces go
    through the shared ghost.load, so a tampered or oversized one is thinned or dropped, never trusted."""
    if not isinstance(raw, dict):
        return None
    grade = raw.get("grade")
    clean = ghost_lib.load(raw.get("clean"))
    if grade not in CAREER_GRADE_POINTS or clean is None:
        return None
    return {
        "label": ghost_lib.clean_label(raw.get("label")) or "Best run",
        "grade": grade,
        "score": round(float(_career_number(raw.get("score"), 0.0, 0.0, 100.0)), 1),
        "clean": clean,
        "funds": ghost_lib.load(raw.get("funds")),
    }


def _ghost_from_history(history, runs):
    """Z-3c: the best finished run in a history list (highest score, the latest on a tie, at least two
    rounds and two clean-share points) as a ghost dict built from the series it already stored, or None.
    This is how a save from before the shared ghost loads: nothing is lost, the old series become the trace."""
    best, best_index = None, -1
    for index, record in enumerate(history):
        if len(record["clean"]) < 2 or record["rounds"] < 2:
            continue
        if best is None or record["score"] >= best["score"]:
            best, best_index = record, index
    if best is None:
        return None
    label = f"Run {max(0, runs - len(history)) + best_index + 1}"
    clean = ghost_lib.make_trace(best["clean"], turns=best["rounds"], label=label)
    if clean is None:
        return None
    return {
        "label": label,
        "grade": best["grade"],
        "score": best["score"],
        "clean": clean,
        "funds": ghost_lib.make_trace(best["funds_series"], turns=best["rounds"], label=label),
    }


def run_ghost_traces(clean_fractions, funds, label=""):
    """Z-3c: the finished run's clean share (percent) and funds as two shared ghost traces, fed one round at
    a time through ghost.Recorder. None when the run was too short (fewer than two rounds)."""
    clean_rec, funds_rec = ghost_lib.Recorder(), ghost_lib.Recorder()
    for fraction in clean_fractions:
        clean_rec.record(fraction * 100.0)
    for value in funds:
        funds_rec.record(max(0, value))
    clean = clean_rec.trace(label)
    if clean is None:
        return None
    return {"clean": clean, "funds": funds_rec.trace(label) if len(funds) == len(clean_fractions) else None}


def validate_career(raw):
    """Coerce anything (corrupt JSON, hand-edited save) into a valid career
    dict; every bad field falls back to its default."""
    out = _default_career()
    if not isinstance(raw, dict):
        return out
    out["runs"] = int(_career_number(raw.get("runs"), 0, 0, 100000))
    out["points"] = int(_career_number(raw.get("points"), 0, 0, 1000000))
    out["best_score"] = float(_career_number(raw.get("best_score"), 0.0, 0.0, 100.0))
    grade = raw.get("best_grade")
    out["best_grade"] = grade if grade in CAREER_GRADE_POINTS else None
    unlocked = raw.get("unlocked")
    if isinstance(unlocked, list):
        out["unlocked"] = [u for u in unlocked if isinstance(u, str)]
    banked = raw.get("achievements")
    if isinstance(banked, list):
        out["achievements"] = [a for a in banked if isinstance(a, str)][:200]
    out["best_streak"] = int(_career_number(raw.get("best_streak"), 0, 0, 100000))
    r90 = raw.get("best_rounds_to_90")
    out["best_rounds_to_90"] = (
        int(_career_number(r90, 1, 1, 100000))
        if isinstance(r90, (int, float)) and not isinstance(r90, bool) and r90 == r90
        else None
    )
    history = raw.get("history")
    if isinstance(history, list):
        valid = [_validate_run_record(entry) for entry in history]
        out["history"] = [entry for entry in valid if entry is not None][-CAREER_HISTORY_MAX:]
    out["lifetime"] = _validate_lifetime(raw.get("lifetime"))
    # Z-3c: the shared best-run ghost. A save from before it existed has none, so it is migrated from the
    # best finished run in the history (the one ghost_record() used to pick); a bad one is dropped the same way.
    ghost_saved = _validate_career_ghost(raw.get("ghost"))
    if ghost_saved is None:
        ghost_saved = _ghost_from_history(out["history"], out["runs"])
    if ghost_saved is not None:
        out["ghost"] = ghost_saved
    # Never let unlocks exceed what the earned points could have paid for: unknown ids, repeats and
    # nodes whose prerequisites are not owned are dropped, and an overspend is trimmed from the newest end.
    out["unlocked"] = skill_tree.sanitize_owned(CAREER_TREE, out["unlocked"], out["points"], overspend="trim")
    loadout = raw.get("loadout")
    out["loadout"] = loadout if loadout in LOADOUT_NODES and loadout in out["unlocked"] else None
    return out


def career_points_available():
    return skill_tree.points_left(CAREER_TREE, runstate.career["unlocked"], runstate.career["points"])


def _career_storage():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return getattr(js, "localStorage", None)


def load_career_from_storage():
    storage = _career_storage()
    if storage is None:
        return _default_career()
    try:
        raw = storage.getItem(CAREER_STORAGE_KEY)
        return validate_career(json.loads(raw)) if raw else _default_career()
    except Exception:  # noqa: BLE001 -- private mode / corrupt JSON: start fresh
        return _default_career()


def save_career_to_storage():
    if runstate.sandbox_active:  # Z-18: the sandbox never writes the career
        return
    storage = _career_storage()
    if storage is None:
        return
    try:
        storage.setItem(CAREER_STORAGE_KEY, json.dumps(runstate.career))
    except Exception:  # noqa: BLE001 -- a refused write must never break play
        pass


def _sync_perks():
    if runstate.sandbox_active:  # Z-18: every upgrade-tree node is on in the sandbox
        runstate.state.perks = set(SANDBOX_ALL_PERKS)
        return
    runstate.state.perks = set(skill_tree.effects(CAREER_TREE, runstate.career["unlocked"]))
