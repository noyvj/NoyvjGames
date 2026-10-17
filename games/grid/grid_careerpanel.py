"""The Career panel: lines, perk progress, history charts, heatmap, import/export and the upgrade tree's view.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

import skill_tree
from js import document

import grid_runstate as runstate
from grid_rules import (
    CAREER_CHART_RUNS, CAREER_TREE, CAREER_UNLOCKS, CAREER_UNLOCK_ORDER, PLANT_LABEL, PLANT_TYPES, SCENARIOS,
    SCENARIO_ORDER,
)
from grid_career_data import (
    _default_career, _sync_perks, career_points_available, save_career_to_storage, validate_career,
)
from grid_career_actions import run_career_points
from grid_runs import _run_label


def career_panel_lines():
    """Plain-text lines for the Career panel's stat blocks."""
    best = runstate.career["best_grade"] or "none yet"
    stats = (
        f"Runs finished: {runstate.career['runs']}. Best sustained clean score: {runstate.career['best_score']:.0f}/100. "
        f"Best operator grade: {best}. Career points: {career_points_available()} to spend "
        f"({runstate.career['points']} earned in total)."
    )
    points, parts = run_career_points()
    if points > 0:
        preview = f"Finishing this run now would bank {points} point(s): " + ", ".join(parts) + "."
    else:
        preview = parts[0]
    return stats, preview


def career_perk_progress_text(perk_id):
    """C-2: what a perk button says about its price -- the numeric effect,
    and for a locked perk how many points away it is (or that it can be
    bought now)."""
    info = CAREER_UNLOCKS[perk_id]
    if perk_id in runstate.career["unlocked"]:
        return f"Unlocked: {info['label']} ({info['effect']}) -- {info['description']}"
    missing = skill_tree.missing_requirements(CAREER_TREE, runstate.career["unlocked"], perk_id)
    if missing:
        names = ", ".join(CAREER_UNLOCKS[m]["label"] for m in missing)
        return f"{info['label']} ({info['cost']} pts, needs {names} first): {info['effect']} -- {info['description']}"
    gap = info["cost"] - career_points_available()
    status = "ready to unlock" if gap <= 0 else f"{gap} more point(s) needed"
    return f"{info['label']} ({info['cost']} pts, {status}): {info['effect']} -- {info['description']}"


def career_next_perk_text():
    """C-2: one line naming the cheapest perk still locked and its gap."""
    locked = [
        u for u in CAREER_UNLOCK_ORDER
        if u not in runstate.career["unlocked"] and not skill_tree.missing_requirements(CAREER_TREE, runstate.career["unlocked"], u)
    ]
    if not locked:
        if all(u in runstate.career["unlocked"] for u in CAREER_UNLOCK_ORDER):
            return "Every career upgrade is unlocked."
        return "Next upgrades need an earlier node in their branch first."
    perk_id = min(locked, key=lambda u: CAREER_UNLOCKS[u]["cost"])
    info = CAREER_UNLOCKS[perk_id]
    gap = info["cost"] - career_points_available()
    if gap <= 0:
        return f"Next perk: {info['label']} ({info['effect']}) -- you can unlock it now."
    return f"Next perk: {info['label']} ({info['effect']}) -- {gap} point(s) away."


def career_records_text():
    """GC-26: the career's personal records, spelled out in words."""
    r90 = runstate.career["best_rounds_to_90"]
    return (
        f"Records: best clean score {runstate.career['best_score']:.0f}/100, best grade {runstate.career['best_grade'] or 'none yet'}, "
        f"fewest rounds to 90% clean {r90 if r90 is not None else 'not reached yet'}, "
        f"longest disruption-free streak {runstate.career['best_streak']} round(s)."
    )


# C-1: the six line styles of the stacked run-comparison charts. Colour is
# never the only cue -- style.css gives each slot its own dash pattern too,
# and the legend repeats each run's line.
RUN_CHART_WIDTH = 280
RUN_CHART_HEIGHT = 64


def career_history_charts_html(history):
    """C-1: three stacked small charts (clean share, funds, demand) with one
    line per run, the six most recent runs, each plotted from its own start
    to its own end so runs of different length stay comparable. Returns ""
    until at least one run has a usable series."""
    runs = [(i, r) for i, r in enumerate(history) if len(r["clean"]) >= 2][-CAREER_CHART_RUNS:]
    if not runs:
        return ""
    charts = [
        ("Clean share of capacity (%)", "clean", 0, 100),
        ("Funds", "funds_series", None, None),
        ("Demand", "demand_series", None, None),
    ]
    out = []
    for title, key, fixed_lo, fixed_hi in charts:
        series = [(i, r[key]) for i, r in runs if len(r[key]) >= 2]
        if not series:
            continue
        lo = fixed_lo if fixed_lo is not None else min(min(v) for _, v in series)
        hi = fixed_hi if fixed_hi is not None else max(max(v) for _, v in series)
        if hi <= lo:
            hi = lo + 1
        lines = []
        for slot, (i, values) in enumerate(series):
            n = len(values)
            points = " ".join(
                f"{j / (n - 1) * RUN_CHART_WIDTH:.1f},{RUN_CHART_HEIGHT - (v - lo) / (hi - lo) * RUN_CHART_HEIGHT:.1f}"
                for j, v in enumerate(values)
            )
            latest = " run-line--latest" if slot == len(series) - 1 else ""
            lines.append(
                f'<polyline points="{points}" class="run-line run-line--{slot}{latest}">'
                f"<title>{_run_label(history, i)}: {values[0]} to {values[-1]}</title></polyline>"
            )
        out.append(
            f'<div class="run-chart"><p class="meter-label">{title} ({lo} to {hi})</p>'
            f'<svg viewBox="0 0 {RUN_CHART_WIDTH} {RUN_CHART_HEIGHT}" class="run-chart-svg" role="img" '
            f'aria-label="{title}, one line per run, start to end of each run">{"".join(lines)}</svg></div>'
        )
    legend = []
    for slot, (i, r) in enumerate(runs):
        legend.append(
            f'<span class="run-legend-item"><svg class="run-legend-swatch" viewBox="0 0 24 6" aria-hidden="true">'
            f'<line x1="0" y1="3" x2="24" y2="3" class="run-line run-line--{slot}" /></svg>'
            f"{_run_label(history, i)} ({r['grade']}, {r['score']:.0f}/100)</span>"
        )
    return "".join(out) + f'<div class="run-legend">{"".join(legend)}</div>'


def career_heatmap_html(history):
    """C-7: clean-share-by-round heatmap, one row per saved run, one cell per
    saved point. A single hue whose strength is the clean share, with the
    exact figure in each cell's tooltip (not colour alone)."""
    rows = []
    for i, r in enumerate(history):
        if not r["clean"]:
            continue
        cells = "".join(
            f'<span class="heat-cell" style="opacity:{0.08 + 0.92 * v / 100:.2f}" '
            f'title="{_run_label(history, i)}, point {j + 1} of {len(r["clean"])}: {v}% clean"></span>'
            for j, v in enumerate(r["clean"])
        )
        rows.append(f'<div class="heat-row"><span class="heat-label">{_run_label(history, i)}</span>'
                    f'<span class="heat-cells">{cells}</span></div>')
    return "".join(rows)


def _grade_from_average(points):
    return "ABCDF"[4 - max(0, min(4, int(round(points))))]


def career_lifetime_lines():
    """C-7: lifetime statistics, in words, from the career's uncapped totals."""
    life = runstate.career["lifetime"]
    if runstate.career["runs"] <= 0:
        return ["No finished runs yet. Finish a run to start your lifetime statistics."]
    lines = [f"Rounds played across {runstate.career['runs']} finished run(s): {life['rounds']}."]
    grades = []
    for scenario in SCENARIO_ORDER:
        entry = life["scenario_grades"].get(scenario)
        if entry:
            letter = _grade_from_average(entry["points"] / entry["n"])
            grades.append(f"{SCENARIOS[scenario]['label']} {letter} ({entry['n']} run(s))")
    lines.append("Average grade per scenario: " + (", ".join(grades) if grades else "none yet") + ".")
    built = life["built"]
    top = max(PLANT_TYPES, key=lambda t: built[t])
    lines.append(
        f"Most-built plant: {PLANT_LABEL[top]} ({built[top]} built)." if built[top] > 0 else "Most-built plant: none yet."
    )
    lines.append(
        f"Disruptions by cause: {life['brownouts']} brownout(s) from emissions, {life['damages']} plant(s) knocked "
        f"offline by emissions, {life['aging']} aging breakdown(s)."
    )
    return lines


def career_history_rows(history):
    """C-1: one plain-text line per saved run, newest first."""
    rows = []
    for i in range(len(history) - 1, -1, -1):
        r = history[i]
        r90 = f", 90% clean by round {r['r90']}" if r["r90"] is not None else ""
        rows.append(
            f"{_run_label(history, i)}: {SCENARIOS[r['scenario']]['label']}, grade {r['grade']}, "
            f"clean score {r['score']:.0f}/100, {r['rounds']} rounds, {r['points']} pt(s) banked, "
            f"final funds {r['funds']}, emissions {r['emissions']}, resilience {r['resilience']}, "
            f"best streak {r['streak']}{r90}."
            + (f" Seed {r['seed']}." if r.get("seed") else "")
            + (" Ironman." if r.get("ironman") else "")
        )
    return rows


def _copy_to_clipboard(text):
    """C-16: best effort -- a browser may refuse (insecure page, no focus),
    in which case the text box is the fallback."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy

        clipboard = getattr(getattr(js, "navigator", None), "clipboard", None)
        if clipboard is None:
            return False
        clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001
        return False


def export_career_to_field():
    """C-16: puts the career JSON in the text box (and on the clipboard when
    allowed). Returns the text."""
    text = json.dumps(runstate.career)
    document.getElementById("career-data-field").value = text
    copied = _copy_to_clipboard(text)
    runstate.career_data_message = (
        "Career data copied to the clipboard and shown in the box." if copied
        else "Career data is in the box below. Select it and copy it to keep a backup."
    )
    return text


def import_career_from_text(text):
    """C-16: replace the career with pasted JSON. Anything that is not a Grid
    career is refused with a message, and nothing changes."""
    if runstate.sandbox_active:
        runstate.career_data_message = "Career backups are switched off in the sandbox."
        return False
    try:
        raw = json.loads(text)
    except (ValueError, TypeError):
        runstate.career_data_message = "That is not valid career data, so nothing was changed."
        return False
    if not isinstance(raw, dict) or not any(k in raw for k in ("runs", "points", "history", "unlocked")):
        runstate.career_data_message = "That does not look like Grid career data, so nothing was changed."
        return False
    runstate.career = validate_career(raw)
    _sync_perks()
    save_career_to_storage()
    runstate.career_data_message = f"Career restored: {runstate.career['runs']} run(s), {runstate.career['points']} point(s) earned."
    return True


def reset_career():
    """C-16: wipe the whole career (points, perks, records, history,
    banked achievements) and return to a fresh start."""
    if runstate.sandbox_active:
        runstate.career_data_message = "The career cannot be reset from the sandbox."
        return
    runstate.career = _default_career()
    runstate.last_finish_records = []
    _sync_perks()
    save_career_to_storage()
    runstate.career_data_message = "Career reset. A copy of the old data stays in the box until you reload the page."


# --- GC-2b / GC-1 / GC-11: the upgrade tree's view --------------------------------------------------------
_career_proxies = []


def _js_window():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return getattr(js, "window", None)


def _to_js(value):
    try:
        from js import Object  # noqa: PLC0415
        from pyodide.ffi import to_js  # noqa: PLC0415
    except ImportError:
        return None
    return to_js(value, dict_converter=Object.fromEntries)


def career_tree_summary_text():
    totals = skill_tree.totals(CAREER_TREE, runstate.career["unlocked"], runstate.career["points"])
    return (
        f"{career_points_available()} career points to spend ({runstate.career['points']} earned in all). "
        f"{totals['owned_count']} of {totals['node_count']} upgrades owned. "
        "Upgrades are permanent and apply to your next run (a run you have not started picks them up at once)."
    )
