"""Levels mode: the level specs, poacher, storm and spirit runs, level status, and the Seed Vault points that levels earn."""

import copy
import json

import skill_tree

import canopy_runstate as runstate
from canopy_achievements import _mature_plot_count, _wildlife_active_count, achievement_ids_earned
from canopy_challenge import challenge_state
from canopy_effects import VAULT_TREE, vault_owned
from canopy_helpers import _gb_hash, _gb_toast, _log_event, _number_or, _plot_ref, _write_local_storage_item
from canopy_rules import ACCRUING_STATES, BARE, DIFFICULTY_NORMAL, DIFFICULTY_RANGER, REPLANTING
from canopy_valuation import standing_forest_value
from canopy_worldvars import (
    CHALLENGE_COMPLETE, CHALLENGE_FAILED, CHALLENGE_NONE, CHALLENGE_NO_HIGHLAND, CHALLENGE_PACIFIST,
    CHALLENGE_SCORCHED, CHALLENGE_SPRINT, HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD, PACE_FREQUENT,
    PACE_NORMAL, PACE_RELAXED, STANDING_TIERS, WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD,
)


# ===========================================================================
# GB batch 3 (2026-10-08): the level select (W-1) with Canopy's modes, and the
# Seed Vault skill tree (W-3) with idle ranger crews.
#
#   * GB-13 Poacher Patrol, GB-15 Storm Front and GB-16 The Spirit's Walk are
#     levels in `levels.json` (every fifth entry), not part of the base game.
#     The four challenge runs from batch 2 are levels too (modes).
#   * GB-10 Seed Vault and GB-26 ranger crews are ONE skill tree (`VAULT_TREE`),
#     drawn by shared/skill-tree.js and validated/bought through
#     shared/skill_tree.py. Seed points are earned from play (never bought,
#     never random); perks are switched off during a challenge run so those
#     stay comparable.
# Same rules as batches 1 and 2: no RNG (hash picks), everything timed rides the
# 1 s tick, new save keys written only when non-default and validated on load.
# Meta-progress (levels done, bests, vault) survives Reset Session: it is kept
# per browser in localStorage and mirrored into every save, and loading a save
# merges it (more progress never gets lost).
# ===========================================================================

META_STORAGE_KEY = "canopy_meta_v1"
LEVEL_MODE_POACHER = "poacher"
LEVEL_MODE_STORM = "storm"
LEVEL_MODE_SPIRIT = "spirit"

# id -> preset and goal. Order = the order in levels.json (a test pins them together).
# goal keys: standing_per_plot, income_per_plot, requests, unlock, challenge, poachers, fronts, spirit.
LEVEL_SPECS = {
    "wren_hollow": {"title": "Wren Hollow", "goal": {"standing_per_plot": 100}},
    "fern_glade": {"title": "Fern Glade", "grid": "small", "goal": {"standing_per_plot": 130}, "requires": ["wren_hollow"]},
    "birch_flats": {"title": "Birch Flats", "grid": "large", "goal": {"standing_per_plot": 100}, "requires": ["wren_hollow"]},
    "ranger_trail": {
        "title": "Ranger Trail", "difficulty": DIFFICULTY_RANGER,
        "goal": {"standing_per_plot": 80, "income_per_plot": 15}, "requires": ["fern_glade"],
    },
    "poacher_patrol": {
        "title": "Poacher Patrol", "mode": LEVEL_MODE_POACHER, "unit": "missed", "goal": {"poachers": 8},
        "requires_count": 3, "unlock_text": "Complete any 3 levels first",
    },
    "quiet_valley": {"title": "Quiet Valley", "pace": PACE_RELAXED, "goal": {"standing_per_plot": 160}, "requires": ["fern_glade"]},
    "busy_valley": {
        "title": "Busy Valley", "pace": PACE_FREQUENT, "goal": {"requests": 3, "standing_per_plot": 70},
        "requires": ["birch_flats"],
    },
    "highland_climb": {"title": "Highland Climb", "goal": {"unlock": "highland"}, "requires": ["ranger_trail"]},
    "wetland_reach": {"title": "Wetland Reach", "goal": {"unlock": "wetland"}, "requires": ["highland_climb"]},
    "storm_front": {
        "title": "Storm Front", "mode": LEVEL_MODE_STORM, "unit": "value lost", "bare_fraction": 0.25, "goal": {"fronts": 4},
        "requires_count": 7, "unlock_text": "Complete any 7 levels first",
    },
    "pacifist": {
        "title": "Pacifist", "challenge": CHALLENGE_PACIFIST, "goal": {"challenge": True},
        "requires_count": 5, "unlock_text": "Complete any 5 levels first",
    },
    "scorched_start": {
        "title": "Scorched Start", "challenge": CHALLENGE_SCORCHED, "goal": {"challenge": True},
        "requires_count": 5, "unlock_text": "Complete any 5 levels first",
    },
    "sprint": {
        "title": "Sprint", "challenge": CHALLENGE_SPRINT, "goal": {"challenge": True},
        "requires_count": 5, "unlock_text": "Complete any 5 levels first",
    },
    "no_highland": {
        "title": "No-Highland", "challenge": CHALLENGE_NO_HIGHLAND, "goal": {"challenge": True},
        "requires_count": 5, "unlock_text": "Complete any 5 levels first",
    },
    "spirits_walk": {
        "title": "The Spirit's Walk", "mode": LEVEL_MODE_SPIRIT, "bare_fraction": 0.25, "goal": {"spirit": True},
        "requires_count": 10, "unlock_text": "Complete any 10 levels first",
    },
}
LEVEL_ORDER = list(LEVEL_SPECS)
LEVEL_RESULT_TEXT_MAX = 60

# --- GB-13: Poacher Patrol ---------------------------------------------------
POACHER_FIRST_TICKS = 8  # the first poacher arrives this many level ticks in
POACHER_STAY_TICKS = 5  # how long a poacher works on a plot before striking
POACHER_MIN_STAY_TICKS = 3  # every 3 driven off, the next stays a tick less, down to this
POACHER_GAP_MIN = 5  # ticks of quiet between one poacher and the next...
POACHER_GAP_SPREAD = 5  # ...plus up to this many more (hash-picked)
POACHER_LOSS_FRACTION = 0.25  # a poacher that strikes takes this share of the plot's standing value

# --- GB-15: Storm Front ---------------------------------------------------------
STORM_INTERVAL_TICKS = 20
STORM_WARNING_TICKS = 8  # the band is shown on the grid this long before the front arrives
STORM_BAND_ROWS = 2
STORM_LOSS_EXPOSED = 0.30  # a plot with a bare or replanting neighbour in its row
STORM_LOSS_EXPOSED_MATURE = 0.15
STORM_LOSS_SHELTERED = 0.05
STORM_LOSS_SHELTERED_MATURE = 0.0

# --- GB-16: The Spirit's Walk -------------------------------------------------------
# (id, what the spirit says, the task in a few words)
SPIRIT_STEPS = [
    ("wake", "I am the quiet between the leaves. Walk with me, ranger. First give the forest a little time: let one plot grow to a value of 10.", "Let one plot reach 10 value"),
    ("tend", "Roots like company. Tend a plot: hover it and press T, or select it and use Tend.", "Tend a plot"),
    ("mend", "Some ground lies bare. Replant a bare plot and let it heal.", "Replant a bare plot"),
    ("life", "Hush. Something small has come home. Let wildlife settle on three plots.", "Wildlife on 3 plots"),
    ("ask", "People live at my edges. When they ask for something, answer them, yes or no. I will not judge.", "Answer one community request"),
    ("grove", "Last, let a grove grow old: four plots fully mature at once.", "4 fully mature plots at once"),
]
SPIRIT_FAREWELL = "Now I can rest. The forest remembers you, and so do I."

# --- GB-10 / GB-26: the Seed Vault ---------------------------------------------------
VAULT_ACHIEVEMENTS_PER_POINT = 4  # 1 seed point per 4 achievements earned (best count ever in this browser)...
VAULT_ACHIEVEMENT_POINTS_MAX = 7  # ...up to this many
CREW_TEND_DELAY_TICKS = 3  # Tend must sit ready this long before the crew uses it (so you can tend first)
CREW_REPLANT_INTERVAL_TICKS = 20
CREW_LEAD_FASTER_TICKS = 8  # the Crew Lead brings the replant interval down by this much

vault_meta = {"best_tier": 0, "best_ach": 0}

poacher_run = {}
storm_run = {}
spirit_run = {}
crew_stats = {"tends": 0, "seedlings": 0, "replants": 0}

_vault_proxies = []

_level_proxies = []


# --- bridges to the shared JS components (all optional: a page or test without them still plays) -----------------

def _js_window():
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return window


def _to_js(value):
    try:
        from js import Object  # noqa: PLC0415
        from pyodide.ffi import to_js  # noqa: PLC0415
    except ImportError:
        return None
    return to_js(value, dict_converter=Object.fromEntries)


def _sync_levels_js():
    """Pushes the saved level progress into the level-select screen (Python owns the state)."""
    window = _js_window()
    levels = getattr(window, "NoyvjLevels", None) if window is not None else None
    payload = _to_js(copy.deepcopy(runstate.levels_state)) if levels is not None else None
    if payload is None:
        return
    try:
        levels.setState(payload)
    except Exception:  # noqa: BLE001 -- a JS-side failure must never break the game
        pass


# --- level progress (the Python twin of the level-select state rules) --------------------------------------------

def _sanitize_levels_state(raw):
    state = {"done": [], "best": {}}
    if isinstance(raw, list):
        raw = {"done": raw}
    if not isinstance(raw, dict):
        return state
    done = raw.get("done")
    for level_id in done if isinstance(done, list) else []:
        if isinstance(level_id, str) and level_id in LEVEL_SPECS and level_id not in state["done"]:
            state["done"].append(level_id)
    best = raw.get("best")
    for level_id, entry in best.items() if isinstance(best, dict) else []:
        if level_id not in state["done"] or not isinstance(entry, dict):
            continue
        clean = {}
        value = _number_or(entry.get("value"), None, float("-inf"))
        if value is not None:
            clean["value"] = value
        text = entry.get("text")
        if isinstance(text, str) and text.strip():
            clean["text"] = text.strip()[:LEVEL_RESULT_TEXT_MAX]
        if clean:
            state["best"][level_id] = clean
    return state


def _better_result(candidate, current):
    """Lower is better for every Canopy level; a text-only result never replaces a numbered best."""
    if current is None:
        return True
    if "value" not in candidate or "value" not in current:
        return False
    return candidate["value"] < current["value"]


def record_level_result(level_id, value, text=""):
    """Marks a level done and keeps the best (lowest) result. Returns True when anything changed."""
    if level_id not in LEVEL_SPECS:
        return False
    changed = False
    if level_id not in runstate.levels_state["done"]:
        runstate.levels_state["done"].append(level_id)
        changed = True
    entry = {}
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
        entry["value"] = value
    if isinstance(text, str) and text.strip():
        entry["text"] = text.strip()[:LEVEL_RESULT_TEXT_MAX]
    if entry and _better_result(entry, runstate.levels_state["best"].get(level_id)):
        runstate.levels_state["best"][level_id] = entry
        changed = True
    if changed:
        _save_meta()
        _sync_levels_js()
    return changed


def _merge_levels_state(base, other):
    merged = {"done": list(base["done"]), "best": dict(base["best"])}
    for level_id in other["done"]:
        if level_id not in merged["done"]:
            merged["done"].append(level_id)
    for level_id, entry in other["best"].items():
        if _better_result(entry, merged["best"].get(level_id)):
            merged["best"][level_id] = entry
    merged["done"].sort(key=LEVEL_ORDER.index)
    return merged


def level_lock_reason(level_id):
    """"" when the level can be played, else why not (same wording rules as shared/level-select.js)."""
    spec = LEVEL_SPECS.get(level_id)
    if spec is None:
        return "Unknown level"
    done = runstate.levels_state["done"]
    missing = [r for r in spec.get("requires", []) if r not in done]
    if missing:
        return spec.get("unlock_text") or "Complete " + " and ".join(LEVEL_SPECS[r]["title"] for r in missing) + " first"
    need = spec.get("requires_count", 0)
    have = len([d for d in done if d != level_id])
    if need > have:
        gap = need - have
        return spec.get("unlock_text") or f"Complete {gap} more level{'' if gap == 1 else 's'} first"
    return ""


def level_number(level_id):
    return LEVEL_ORDER.index(level_id) + 1


def _level_mode():
    return LEVEL_SPECS[runstate.current_level].get("mode") if runstate.current_level in LEVEL_SPECS else None


def _level_matches_settings(spec):
    return (
        runstate.current_grid_size == spec.get("grid", "normal")
        and runstate.current_difficulty == spec.get("difficulty", DIFFICULTY_NORMAL)
        and runstate.current_challenge == spec.get("challenge", CHALLENGE_NONE)
        and runstate.current_pace == spec.get("pace", PACE_NORMAL)
    )


def next_level_id():
    """GN-3: the level after the current one in the level list, or None (no level running, or the last one)."""
    if runstate.current_level not in LEVEL_SPECS:
        return None
    index = LEVEL_ORDER.index(runstate.current_level) + 1
    return LEVEL_ORDER[index] if index < len(LEVEL_ORDER) else None


def _burn_level_start():
    """Levels with a bare_fraction begin with that share of plots bare (hash-picked, soil untouched)."""
    spec = LEVEL_SPECS.get(runstate.current_level)
    fraction = spec.get("bare_fraction", 0) if spec else 0
    if not fraction:
        return
    count = int(round(len(runstate.plots) * fraction))
    for index in sorted(range(len(runstate.plots)), key=lambda i: (_gb_hash(i, 23), i))[:count]:
        plot = runstate.plots[index]
        plot.state = BARE
        plot.value = 0.0
        plot.ticks_intact = 0
        plot.biodiversity = 0.0


def _reset_level_run(reset_crews=True):
    """Fresh run state for the current level (or none) and, normally, the session's crew counters."""
    runstate.level_ticks = 0
    runstate.level_done_tick = None
    poacher_run.clear()
    storm_run.clear()
    spirit_run.clear()
    if reset_crews:
        for key in crew_stats:
            crew_stats[key] = 0
        runstate._crew_tend_wait = 0
        runstate._crew_replant_clock = 0
    mode = _level_mode()
    if mode == LEVEL_MODE_POACHER:
        poacher_run.update(plot=None, ticks_left=0, driven=0, missed=0, next_in=POACHER_FIRST_TICKS, last_plot=None)
    elif mode == LEVEL_MODE_STORM:
        storm_run.update(next_in=STORM_INTERVAL_TICKS, fronts=0, lost=0.0, hits=0, shielded=0)
    elif mode == LEVEL_MODE_SPIRIT:
        spirit_run.update(step=0, said=-1)


# --- goals --------------------------------------------------------------------------------------------------------

def level_goal_parts():
    """[(text, met)] for each part of the current level's goal."""
    spec = LEVEL_SPECS[runstate.current_level]
    goal = spec["goal"]
    n = len(runstate.plots)
    parts = []
    if "standing_per_plot" in goal:
        need = goal["standing_per_plot"] * n
        have = standing_forest_value()
        parts.append((f"standing value {have:.0f} of {need}", have >= need))
    if "income_per_plot" in goal:
        need = goal["income_per_plot"] * n
        parts.append((f"income {runstate.total_income:.0f} of {need}", runstate.total_income >= need))
    if "requests" in goal:
        answered = runstate.stakeholder_grants_count + runstate.stakeholder_declines_count
        parts.append((f"requests answered {min(answered, goal['requests'])} of {goal['requests']}", answered >= goal["requests"]))
    if goal.get("unlock") == "highland":
        parts.append(("Highland Grove open" if runstate.highland_unlocked else
                      f"standing value {standing_forest_value():.0f} of {HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f}", runstate.highland_unlocked))
    if goal.get("unlock") == "wetland":
        parts.append(("Wetland Forest open" if runstate.wetland_unlocked else
                      f"standing value {standing_forest_value():.0f} of {WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f}", runstate.wetland_unlocked))
    if goal.get("challenge"):
        state = challenge_state()
        label = {CHALLENGE_COMPLETE: "challenge complete", CHALLENGE_FAILED: "challenge failed (Reset Session to retry)"}.get(state, "challenge in progress")
        parts.append((label, state == CHALLENGE_COMPLETE))
    if "poachers" in goal and poacher_run:
        driven = poacher_run["driven"]
        parts.append((f"poachers driven off {min(driven, goal['poachers'])} of {goal['poachers']}", driven >= goal["poachers"]))
    if "fronts" in goal and storm_run:
        fronts = storm_run["fronts"]
        parts.append((f"storm fronts weathered {min(fronts, goal['fronts'])} of {goal['fronts']}", fronts >= goal["fronts"]))
    if goal.get("spirit") and spirit_run:
        step = spirit_run["step"]
        parts.append((f"spirit's tasks {min(step, len(SPIRIT_STEPS))} of {len(SPIRIT_STEPS)}", step >= len(SPIRIT_STEPS)))
    return parts


def _level_goal_met():
    parts = level_goal_parts()
    return bool(parts) and all(met for _text, met in parts)


def _level_result():
    """(value, text) of the finished level: ticks, or the mode's own measure (both lower is better)."""
    mode = _level_mode()
    if mode == LEVEL_MODE_POACHER:
        missed = poacher_run["missed"]
        return missed, f"{missed} missed"
    if mode == LEVEL_MODE_STORM:
        lost = int(round(storm_run["lost"]))
        return lost, f"{lost} value lost"
    return runstate.level_ticks, f"{runstate.level_ticks} ticks"


def _complete_level():
    runstate.level_done_tick = runstate.level_ticks
    spec = LEVEL_SPECS[runstate.current_level]
    value, text = _level_result()
    previous = runstate.levels_state["best"].get(runstate.current_level)
    first_time = runstate.current_level not in runstate.levels_state["done"]
    record_level_result(runstate.current_level, value, text)
    if poacher_run:
        poacher_run["plot"] = None
    if _level_mode() == LEVEL_MODE_SPIRIT:
        _log_event("spirit", f"Forest spirit: {SPIRIT_FAREWELL}", None)
    note = " (new best)" if previous is not None and _better_result({"value": value}, previous) else ""
    _log_event("level", f"Level {level_number(runstate.current_level)} complete: {spec['title']} in {text}{note}", None)
    _gb_toast(f"\U0001F5FA️ Level complete: {spec['title']}{' (first time)' if first_time else ''}")
    _note_vault_progress()


def _advance_level():
    """The per-tick hook: counts the level's own clock, runs its mode, then checks the goal."""
    if runstate.current_level is None or runstate.level_done_tick is not None:
        return
    runstate.level_ticks += 1
    mode = _level_mode()
    if mode == LEVEL_MODE_POACHER:
        _advance_poachers()
    elif mode == LEVEL_MODE_STORM:
        _advance_storm()
    elif mode == LEVEL_MODE_SPIRIT:
        _advance_spirit()
    if _level_goal_met():
        _complete_level()


# --- GB-13: Poacher Patrol --------------------------------------------------------------------------------

def poacher_stay_ticks():
    return max(POACHER_MIN_STAY_TICKS, POACHER_STAY_TICKS - poacher_run.get("driven", 0) // 3)


def _poacher_gap():
    return POACHER_GAP_MIN + _gb_hash(runstate.forest_tick, poacher_run["driven"], poacher_run["missed"], 43) % POACHER_GAP_SPREAD


def _active_poacher_plot():
    if _level_mode() != LEVEL_MODE_POACHER or runstate.level_done_tick is not None or not poacher_run:
        return None
    return poacher_run["plot"]


def _advance_poachers():
    run = poacher_run
    if run["plot"] is not None:
        plot = runstate.plots[run["plot"]]
        run["ticks_left"] -= 1
        if plot.state not in ACCRUING_STATES:  # the plot was cleared first: the poacher gives up
            run["plot"] = None
            run["next_in"] = _poacher_gap()
        elif run["ticks_left"] <= 0:
            loss = plot.value * POACHER_LOSS_FRACTION
            plot.value -= loss
            run["missed"] += 1
            _log_event("poacher", f"A poacher struck {_plot_ref(plot.index)} and took {loss:.1f} value", plot.index)
            run["last_plot"] = run["plot"]
            run["plot"] = None
            run["next_in"] = _poacher_gap()
        return
    run["next_in"] -= 1
    if run["next_in"] > 0:
        return
    candidates = [p.index for p in runstate.plots if p.state in ACCRUING_STATES and p.index != run.get("last_plot")]
    if not candidates:
        candidates = [p.index for p in runstate.plots if p.state in ACCRUING_STATES]
    if not candidates:
        run["next_in"] = 1  # nothing standing to poach; look again next tick
        return
    index = candidates[_gb_hash(runstate.forest_tick, run["driven"], run["missed"], 41) % len(candidates)]
    run["plot"] = index
    run["ticks_left"] = poacher_stay_ticks()
    _log_event("poacher", f"A poacher is working on {_plot_ref(index)}: click it (or press P) within {run['ticks_left']} ticks", index)


def drive_off_poacher(index=None):
    """Clicking the poacher's plot (or P) drives it off. `index` is the clicked plot; P passes nothing."""
    run = poacher_run
    if _active_poacher_plot() is None:
        return False
    if index is not None and index != run["plot"]:
        return False
    plot_index = run["plot"]
    run["driven"] += 1
    run["last_plot"] = plot_index
    run["plot"] = None
    run["next_in"] = _poacher_gap()
    _log_event("poacher", f"Drove off a poacher at {_plot_ref(plot_index)} ({run['driven']} of {LEVEL_SPECS[runstate.current_level]['goal']['poachers']})", plot_index)
    return True


# --- GB-15: Storm Front ------------------------------------------------------------------------------------------

def _storm_band_rows(front_number):
    """The two rows front number `front_number` (1-based) will cross: a pure function of the number."""
    span = max(1, runstate.GRID_ROWS - STORM_BAND_ROWS + 1)
    first = _gb_hash(front_number, runstate.GRID_ROWS, 53) % span
    return tuple(range(first, first + STORM_BAND_ROWS))


def _storm_warning_rows():
    if _level_mode() != LEVEL_MODE_STORM or runstate.level_done_tick is not None or not storm_run:
        return ()
    if storm_run["next_in"] > STORM_WARNING_TICKS:
        return ()
    return _storm_band_rows(storm_run["fronts"] + 1)


def _storm_exposed(index):
    """A plot is exposed when its left or right neighbour in the same row is a gap (bare or replanting)."""
    col = index % runstate.GRID_COLS
    for step in (-1, 1):
        if 0 <= col + step < runstate.GRID_COLS and runstate.plots[index + step].state in (BARE, REPLANTING):
            return True
    return False


def _advance_storm():
    run = storm_run
    run["next_in"] -= 1
    if run["next_in"] > 0:
        return
    rows = _storm_band_rows(run["fronts"] + 1)
    lost = 0.0
    hit = 0
    shielded = 0
    for plot in runstate.plots:
        if plot.index // runstate.GRID_COLS not in rows or plot.state not in ACCRUING_STATES:
            continue
        mature = plot.maturity_fraction() >= 1.0
        if _storm_exposed(plot.index):
            fraction = STORM_LOSS_EXPOSED_MATURE if mature else STORM_LOSS_EXPOSED
        else:
            fraction = STORM_LOSS_SHELTERED_MATURE if mature else STORM_LOSS_SHELTERED
        taken = plot.value * fraction
        plot.value -= taken
        lost += taken
        if taken > 0:
            hit += 1
        else:
            shielded += 1
    run["fronts"] += 1
    run["lost"] += lost
    run["hits"] += hit
    run["shielded"] += shielded
    run["next_in"] = STORM_INTERVAL_TICKS
    first, last = rows[0] + 1, rows[-1] + 1
    _log_event("storm", f"Storm front {run['fronts']} crossed rows {first}-{last}: {lost:.1f} value lost, {shielded} plots untouched", None)
    _gb_toast(f"⛈️ Storm front {run['fronts']} passed rows {first}-{last}: {lost:.0f} value lost")


# --- GB-16: The Spirit's Walk ------------------------------------------------------------------------------------

def _spirit_step_done(step_id):
    if step_id == "wake":
        return any(plot.value >= 10 for plot in runstate.plots)
    if step_id == "tend":
        return runstate.tends_done >= 1
    if step_id == "mend":
        return runstate.total_replants >= 1
    if step_id == "life":
        return _wildlife_active_count() >= 3
    if step_id == "ask":
        return runstate.stakeholder_grants_count + runstate.stakeholder_declines_count >= 1
    if step_id == "grove":
        return _mature_plot_count() >= min(4, len(runstate.plots))
    return False


def _advance_spirit():
    run = spirit_run
    while run["step"] < len(SPIRIT_STEPS):
        step = run["step"]
        if run["said"] < step:
            run["said"] = step
            _log_event("spirit", f"Forest spirit: {SPIRIT_STEPS[step][1]}", None)
        if not _spirit_step_done(SPIRIT_STEPS[step][0]):
            return
        run["step"] += 1


def spirit_line_text():
    """What the spirit is saying right now ("" outside her level)."""
    if _level_mode() != LEVEL_MODE_SPIRIT or not spirit_run:
        return ""
    if runstate.level_done_tick is not None or spirit_run["step"] >= len(SPIRIT_STEPS):
        return SPIRIT_FAREWELL
    return SPIRIT_STEPS[spirit_run["step"]][1]


# --- the level box (status, spirit line, leave button) ---------------------------------------------------------

def level_status_text():
    if runstate.current_level is None:
        return ""
    spec = LEVEL_SPECS[runstate.current_level]
    head = f"\U0001F5FA️ Level {level_number(runstate.current_level)}: {spec['title']}"
    best = runstate.levels_state["best"].get(runstate.current_level)
    best_text = f" · best {best['text']}" if best and best.get("text") else ""
    if runstate.level_done_tick is not None:
        _value, text = _level_result()
        return f"{head} · ✓ complete in {text}{best_text}. You can keep playing or leave the level."
    parts = [text for text, _met in level_goal_parts()]
    mode = _level_mode()
    if mode == LEVEL_MODE_POACHER and poacher_run:
        if poacher_run["plot"] is not None:
            parts.append(f"\U0001FA93 poacher on {_plot_ref(poacher_run['plot'])}: {poacher_run['ticks_left']} ticks to drive it off")
        else:
            parts.append(f"next poacher in about {max(1, poacher_run['next_in'])} ticks")
        parts.append(f"missed {poacher_run['missed']}")
    elif mode == LEVEL_MODE_STORM and storm_run:
        rows = _storm_warning_rows()
        if rows:
            parts.append(f"⛈️ front in {storm_run['next_in']} ticks over rows {rows[0] + 1}-{rows[-1] + 1}")
        else:
            parts.append(f"next front in {storm_run['next_in']} ticks")
        parts.append(f"value lost {storm_run['lost']:.0f}")
    elif mode == LEVEL_MODE_SPIRIT and spirit_run and spirit_run["step"] < len(SPIRIT_STEPS):
        parts.append(f"now: {SPIRIT_STEPS[spirit_run['step']][2]}")
    return f"{head} · " + " · ".join(parts) + f" · {runstate.level_ticks} ticks{best_text}"


def _set_class(element, name, on):
    if on:
        element.classList.add(name)
    else:
        element.classList.remove(name)


def levels_progress_text():
    return f"{len(runstate.levels_state['done'])} of {len(LEVEL_ORDER)} levels complete"


def vault_points_earned():
    """Seed points ever earned: 1 per level completed, 1 per forest tier reached (best ever), 1 per 4 achievements
    (best count ever, up to VAULT_ACHIEVEMENT_POINTS_MAX). Deterministic and never spent away: spending only moves
    points between the balance and the perks."""
    achievement_points = min(VAULT_ACHIEVEMENT_POINTS_MAX, vault_meta["best_ach"] // VAULT_ACHIEVEMENTS_PER_POINT)
    return len(runstate.levels_state["done"]) + vault_meta["best_tier"] + achievement_points


def vault_points_free():
    return skill_tree.points_left(VAULT_TREE, vault_owned, vault_points_earned())


def _save_meta():
    blob = {
        "levels": runstate.levels_state,
        "seed_vault": {"owned": list(vault_owned), "best_tier": vault_meta["best_tier"], "best_ach": vault_meta["best_ach"]},
    }
    _write_local_storage_item(META_STORAGE_KEY, json.dumps(blob))


def _note_vault_progress(silent=False):
    """Raises the best-ever tier and achievement counts and toasts a newly earned seed point (not when `silent`)."""
    changed = False
    if runstate.milestone_tier > vault_meta["best_tier"]:
        vault_meta["best_tier"] = min(runstate.milestone_tier, len(STANDING_TIERS))
        changed = True
    count = len(achievement_ids_earned())
    if count > vault_meta["best_ach"]:
        vault_meta["best_ach"] = count
        changed = True
    points = vault_points_earned()
    if changed:
        _save_meta()
    if points > runstate._last_vault_points and not silent:
        gained = points - runstate._last_vault_points
        _gb_toast(f"\U0001F330 +{gained} seed point{'s' if gained != 1 else ''} for the Seed Vault ({vault_points_free()} to spend)")
    runstate._last_vault_points = points
