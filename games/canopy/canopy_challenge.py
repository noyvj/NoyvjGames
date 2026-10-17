"""Scenarios (clear-cut start, remnant) and challenges (Pacifist, Scorched, Sprint ...): records, goals, status and badges."""

import json

from js import document

import canopy_runstate as runstate
from canopy_helpers import (
    _el, _flash_forest_pulse, _gb_hash, _gb_toast, _log_event, _read_local_storage_item,
    _write_local_storage_item,
)
from canopy_rules import BARE, BASE_ACCRUAL, SCENARIO_NONE, lab_active
from canopy_valuation import _total_clear_count, standing_forest_value
from canopy_worldvars import (
    CHALLENGE_ACTIVE, CHALLENGE_COMPLETE, CHALLENGE_FAILED, CHALLENGE_NONE, CHALLENGE_NO_HIGHLAND,
    CHALLENGE_NO_HIGHLAND_STANDING_PER_PLOT, CHALLENGE_PACIFIST, CHALLENGE_PACIFIST_STANDING_PER_PLOT,
    CHALLENGE_RECORDS_STORAGE_KEY, CHALLENGE_SCORCHED, CHALLENGE_SCORCHED_BARE_FRACTION,
    CHALLENGE_SCORCHED_STANDING_PER_PLOT, CHALLENGE_SPECS, CHALLENGE_SPRINT,
    CHALLENGE_SPRINT_INCOME_PER_PLOT, CHALLENGE_SPRINT_STANDING_PER_PLOT, CHALLENGE_SPRINT_TICK_LIMIT,
)


# --- B-6: request pace ---------------------------------------------------------------------------------------


# --- GB-17: challenge runs -----------------------------------------------------------------------------------
SCENARIO_SPECS = {
    "clearcut": {"label": "Clear-cut Valley", "blurb": "60% of the plots start bare."},
    "farmland": {"label": "Fragmented Farmland", "blurb": "A checkerboard: every other plot starts bare."},
    "remnant": {"label": "Old-Growth Remnant", "blurb": "Only one intact core of old growth is left; everything else is bare."},
}
SCENARIO_CLEARCUT_BARE_FRACTION = 0.6
SCENARIO_REMNANT_HEAD_START_TICKS = 40
SCENARIO_BESTS_STORAGE_KEY = "canopy_scenario_bests_v1"
runstate.current_scenario = SCENARIO_NONE


def scenario_bare_indexes(scenario, rows, cols):
    """Which plot indexes start bare for a scenario on a rows x cols grid (a pure function, so it is testable)."""
    count = rows * cols
    if scenario == "clearcut":
        bare_count = int(round(count * SCENARIO_CLEARCUT_BARE_FRACTION))
        return set(sorted(range(count), key=lambda i: (_gb_hash(i, 29), i))[:bare_count])
    if scenario == "farmland":
        return {r * cols + c for r in range(rows) for c in range(cols) if (r + c) % 2 == 0}
    if scenario == "remnant":
        centre_r, centre_c = rows // 2, cols // 2
        core = {r * cols + c for r in range(rows) for c in range(cols) if abs(r - centre_r) <= 1 and abs(c - centre_c) <= 1}
        return set(range(count)) - core
    return set()


def _apply_scenario_start():
    """Called by reset_session() after the plots exist. Skipped while a challenge or a level is running."""
    if runstate.current_scenario == SCENARIO_NONE or runstate.current_challenge != CHALLENGE_NONE or runstate.current_level is not None:
        return
    bare = scenario_bare_indexes(runstate.current_scenario, runstate.GRID_ROWS, runstate.GRID_COLS)
    for plot in runstate.plots:
        if plot.index in bare:
            plot.state = BARE
            plot.value = 0.0
            plot.ticks_intact = 0
            plot.biodiversity = 0.0
        elif runstate.current_scenario == "remnant":
            plot.ticks_intact = SCENARIO_REMNANT_HEAD_START_TICKS
            plot.value = BASE_ACCRUAL * SCENARIO_REMNANT_HEAD_START_TICKS


def load_scenario_bests():
    raw = _read_local_storage_item(SCENARIO_BESTS_STORAGE_KEY)
    out = {}
    if raw:
        try:
            data = json.loads(raw)
        except ValueError:
            data = {}
        if isinstance(data, dict):
            for key in SCENARIO_SPECS:
                try:
                    out[key] = max(0.0, float(data.get(key, 0.0)))
                except (TypeError, ValueError):
                    continue
    return out


def _update_scenario_best():
    """Called every render(): keeps the running scenario's own best standing value."""
    if runstate.current_scenario == SCENARIO_NONE or runstate.current_scenario not in SCENARIO_SPECS or lab_active():
        return
    bests = load_scenario_bests()
    value = standing_forest_value()
    if value > bests.get(runstate.current_scenario, 0.0):
        bests[runstate.current_scenario] = round(value, 2)
        _write_local_storage_item(SCENARIO_BESTS_STORAGE_KEY, json.dumps(bests))


def scenario_best_text():
    if runstate.current_scenario not in SCENARIO_SPECS:
        return ""
    label = SCENARIO_SPECS[runstate.current_scenario]["label"]
    best = load_scenario_bests().get(runstate.current_scenario, 0.0)
    return f"{label} best: standing {best:.1f}" if best > 0 else f"{label}: no best yet"


def render_scenario_best():
    element = _el("scenario-best-display")
    if element is None:
        return
    text = scenario_best_text()
    element.innerText = text
    element.hidden = not text


def _apply_challenge_start():
    """Called by reset_session() once the plots exist. Scorched Start burns two thirds of the forest."""
    if runstate.current_challenge == CHALLENGE_SCORCHED:
        count = int(round(len(runstate.plots) * CHALLENGE_SCORCHED_BARE_FRACTION))
        for index in sorted(range(len(runstate.plots)), key=lambda i: (_gb_hash(i, 17), i))[:count]:
            plot = runstate.plots[index]
            plot.state = BARE
            plot.value = 0.0
            plot.ticks_intact = 0
            plot.biodiversity = 0.0
    runstate.contract_clear_count_seen = _total_clear_count()
    runstate.contract_last_clear_tick = 0


def _challenge_regions_cleared():
    return any(p.clear_count for p in runstate.highland_plots) or any(p.clear_count for p in runstate.wetland_plots)


def challenge_goal():
    """(standing goal, income goal) for the current challenge; income goal is 0 unless Sprint."""
    n = len(runstate.plots)
    if runstate.current_challenge == CHALLENGE_PACIFIST:
        return CHALLENGE_PACIFIST_STANDING_PER_PLOT * n, 0
    if runstate.current_challenge == CHALLENGE_SCORCHED:
        return CHALLENGE_SCORCHED_STANDING_PER_PLOT * n, 0
    if runstate.current_challenge == CHALLENGE_NO_HIGHLAND:
        return CHALLENGE_NO_HIGHLAND_STANDING_PER_PLOT * n, 0
    if runstate.current_challenge == CHALLENGE_SPRINT:
        return CHALLENGE_SPRINT_STANDING_PER_PLOT * n, CHALLENGE_SPRINT_INCOME_PER_PLOT * n
    return 0, 0


def challenge_rule_text():
    standing, income = challenge_goal()
    if runstate.current_challenge == CHALLENGE_PACIFIST:
        return f"reach {standing} standing value without clearing any plot (a granted request counts as a clear)"
    if runstate.current_challenge == CHALLENGE_SCORCHED:
        return f"start with two thirds of the plots bare, then reach {standing} standing value"
    if runstate.current_challenge == CHALLENGE_SPRINT:
        return (
            f"within {CHALLENGE_SPRINT_TICK_LIMIT} ticks, bank {income} income and hold "
            f"{standing} standing value at the same time"
        )
    if runstate.current_challenge == CHALLENGE_NO_HIGHLAND:
        return f"reach {standing} standing value with Highland Grove and Wetland Forest sealed"
    return ""


def challenge_state():
    """None (no challenge), or active / complete / failed. Failure is read off the live forest, so an
    undone clear does not fail a Pacifist run."""
    if runstate.current_challenge == CHALLENGE_NONE:
        return None
    if runstate.challenge_complete_tick is not None:
        return CHALLENGE_COMPLETE
    if runstate.current_challenge == CHALLENGE_PACIFIST and (_total_clear_count() > 0 or _challenge_regions_cleared()):
        return CHALLENGE_FAILED
    if runstate.current_challenge == CHALLENGE_SPRINT and runstate.forest_tick > CHALLENGE_SPRINT_TICK_LIMIT:
        return CHALLENGE_FAILED
    return CHALLENGE_ACTIVE


def _challenge_goal_met():
    standing, income = challenge_goal()
    if standing <= 0:
        return False
    return standing_forest_value() >= standing and runstate.total_income >= income


def load_challenge_records():
    if runstate._challenge_record_cache is None:
        records = {}
        raw = _read_local_storage_item(CHALLENGE_RECORDS_STORAGE_KEY)
        if raw:
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if key in CHALLENGE_SPECS and isinstance(value, int) and not isinstance(value, bool) and value > 0:
                        records[key] = value
        runstate._challenge_record_cache = records
    return runstate._challenge_record_cache


def challenge_badge_earned(challenge_id):
    """A badge is permanent in this browser: finishing a challenge once keeps it, whatever the session does next."""
    if challenge_id in load_challenge_records():
        return True
    return runstate.current_challenge == challenge_id and runstate.challenge_complete_tick is not None


def _record_challenge_completion(tick):
    records = load_challenge_records()
    best = records.get(runstate.current_challenge)
    if best is None or tick < best:
        records[runstate.current_challenge] = max(1, int(tick))
        _write_local_storage_item(CHALLENGE_RECORDS_STORAGE_KEY, json.dumps(records))


def _check_challenge():
    if challenge_state() != CHALLENGE_ACTIVE or not _challenge_goal_met():
        return
    runstate.challenge_complete_tick = runstate.forest_tick
    label = CHALLENGE_SPECS[runstate.current_challenge]["label"]
    _record_challenge_completion(runstate.forest_tick)
    _log_event("challenge", f"{label} challenge complete in {runstate.forest_tick} ticks", None)
    _gb_toast(f"{CHALLENGE_SPECS[runstate.current_challenge]['icon']} {label} challenge complete: badge earned")
    _flash_forest_pulse()


def challenge_status_text():
    state = challenge_state()
    if state is None:
        return ""
    spec = CHALLENGE_SPECS[runstate.current_challenge]
    head = f"{spec['icon']} Challenge: {spec['label']} · {challenge_rule_text()}"
    standing, income = challenge_goal()
    best = load_challenge_records().get(runstate.current_challenge)
    best_text = f" Your fastest finish: {best} ticks." if best else ""
    if state == CHALLENGE_COMPLETE:
        return f"{head}. Complete in {runstate.challenge_complete_tick} ticks, badge earned.{best_text}"
    if state == CHALLENGE_FAILED:
        why = "a plot was cleared" if runstate.current_challenge == CHALLENGE_PACIFIST else "time ran out"
        return f"{head}. Failed ({why}). Reset Session to retry.{best_text}"
    if runstate.current_challenge == CHALLENGE_SPRINT:
        progress = (
            f"standing {int(standing_forest_value())}/{standing}, income {int(runstate.total_income)}/{income}, "
            f"{max(0, CHALLENGE_SPRINT_TICK_LIMIT - runstate.forest_tick)} ticks left"
        )
    else:
        progress = f"standing {int(standing_forest_value())}/{standing}"
    return f"{head}. In progress: {progress}.{best_text}"


def render_challenge_status():
    element = _el("challenge-status")
    if element is None:
        return
    text = challenge_status_text()
    element.hidden = not text
    element.innerText = text
    state = challenge_state()
    for name in (CHALLENGE_ACTIVE, CHALLENGE_COMPLETE, CHALLENGE_FAILED):
        if name == state:
            element.classList.add(f"challenge-status--{name}")
        else:
            element.classList.remove(f"challenge-status--{name}")


def challenge_badge_entries():
    """[(icon, label, earned, best_ticks_or_None)] for the Almanac."""
    records = load_challenge_records()
    return [
        (spec["icon"], spec["label"], challenge_badge_earned(cid), records.get(cid))
        for cid, spec in CHALLENGE_SPECS.items()
    ]


def render_challenge_badges(panel):
    """Appends the Almanac's challenge-badge row."""
    entries = challenge_badge_entries()
    heading = document.createElement("h3")
    heading.className = "almanac-heading"
    heading.innerText = f"Challenge badges ({sum(1 for e in entries if e[2])}/{len(entries)})"
    panel.appendChild(heading)
    row = document.createElement("ul")
    row.className = "almanac-list"
    for icon, label, earned, best in entries:
        item = document.createElement("li")
        item.className = "almanac-item almanac-item--found" if earned else "almanac-item almanac-item--unfound"
        item.setAttribute("aria-label", f"{label} challenge: {'badge earned' if earned else 'not yet finished'}")
        glyph = document.createElement("span")
        glyph.className = "almanac-icon" if earned else "almanac-icon almanac-silhouette"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = icon
        item.appendChild(glyph)
        text = document.createElement("span")
        text.className = "almanac-name"
        text.innerText = (f"{label} ({best} ticks)" if best else label) if earned else "???"
        item.appendChild(text)
        row.appendChild(item)
    panel.appendChild(row)
