"""The Harbor Almanac (lifetime counts and bests) and the season planner."""

import copy
import html
import json

from js import document

import tide_runstate as runstate
from tide_bridge import _clamped_int, _finite_number, _read_local_storage_item, _write_local_storage_item
from tide_coasts import heritage_sites
from tide_graphs import SPARKLINE_HEIGHT, SPARKLINE_WIDTH, _crosshair_attr, _series_svg, _xy
from tide_rules import (
    ADAPTATION_TIERS, ALMANAC_KEY, CATEGORIES, COASTLINE_ROWS, DEFAULT_COASTLINE, DIVERSIFY_MAX_LEVEL,
    FISH_DAMAGE_SCALE, PLANNER_MAX_PER_CATEGORY, PLANNER_MAX_SEASONS, PLANNER_RISK_SEASONS,
    RETREAT_MAX_STEPS, SEA_SCENARIOS, TIER_BADGES,
)


# ---- D-9 Harbor Almanac ----------------------------------------------------
ALMANAC_LIFETIME = [
    ("seasons", "Seasons played"),
    ("rows_kept", "Rows kept dry (counted each season)"),
    ("heritage", "Heritage sites protected"),
    ("storms", "Storms weathered"),
]


def _empty_almanac():
    return {key: 0 for key, _label in ALMANAC_LIFETIME} | {"best": {}}


def _load_almanac():
    data = _empty_almanac()
    raw = _read_local_storage_item(ALMANAC_KEY)
    if not raw:
        return data
    try:
        saved = json.loads(raw)
    except (ValueError, TypeError):
        return data
    if not isinstance(saved, dict):
        return data
    for key, _label in ALMANAC_LIFETIME:
        value = saved.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10**9:
            data[key] = value
    best = saved.get("best")
    if isinstance(best, dict):
        for combo, entry in best.items():
            scenario, _sep, lag = str(combo).partition("|")
            if (
                scenario in SEA_SCENARIOS and lag in ("standard", "hard") and isinstance(entry, dict)
                and _finite_number(entry.get("score"), -1e9, 1e9)
                and isinstance(entry.get("seasons"), int) and 0 <= entry["seasons"] <= 10**6
                and isinstance(entry.get("tier"), int) and 0 <= entry["tier"] < len(ADAPTATION_TIERS)
                and isinstance(entry.get("rows_dry"), int) and 0 <= entry["rows_dry"] <= COASTLINE_ROWS
            ):
                data["best"][combo] = {
                    "score": round(float(entry["score"]), 1), "seasons": entry["seasons"],
                    "tier": entry["tier"], "rows_dry": entry["rows_dry"],
                    "retreat": _clamped_int(entry.get("retreat"), 0, RETREAT_MAX_STEPS),
                    "tourism": _clamped_int(entry.get("tourism"), 0, DIVERSIFY_MAX_LEVEL),
                    "aquaculture": _clamped_int(entry.get("aquaculture"), 0, DIVERSIFY_MAX_LEVEL),
                    "heritage": _clamped_int(entry.get("heritage"), 0, len(heritage_sites())),
                }
    return data


runstate.almanac = _empty_almanac()  # filled from localStorage just before setup(), once every helper exists
# Where the almanac has counted up to in THIS run (so loading a save or rewinding to a
# checkpoint never counts the same season twice).
_almanac_cursor = {"season": 1, "protected": 0}


def almanac_combo_key():
    return f"{runstate.state.sea_scenario}|{'hard' if runstate.state.hard_lag_mode else 'standard'}"


def almanac_resync():
    _almanac_cursor["season"] = runstate.state.season
    _almanac_cursor["protected"] = runstate.state.protected_heritage_count()


def almanac_sync():
    """Adds whatever happened since the last call to the lifetime totals and updates the
    personal best for this scenario and lag mode. Called from render(), so it is idempotent."""
    cursor = _almanac_cursor
    if runstate.state.keeps_records_out():  # D-5 / GD-5: custom-rule and daily runs are not counted in the Almanac
        cursor["season"] = runstate.state.season
        return
    if runstate.state.season < cursor["season"]:
        cursor["season"] = runstate.state.season
    new_seasons = runstate.state.season - cursor["season"]
    changed = False
    if new_seasons > 0:
        runstate.almanac["seasons"] += new_seasons
        for entry in runstate.state.season_ledger:
            if cursor["season"] <= entry["season"] < runstate.state.season:
                runstate.almanac["rows_kept"] += entry["rows_dry"]
        for storm in runstate.state.storm_log:
            if cursor["season"] <= storm["season"] < runstate.state.season:
                runstate.almanac["storms"] += 1
        cursor["season"] = runstate.state.season
        changed = True
    protected = runstate.state.protected_heritage_count()
    if protected > cursor["protected"]:
        runstate.almanac["heritage"] += protected - cursor["protected"]
        changed = True
    cursor["protected"] = protected
    if new_seasons > 0 and runstate.state.coastline == DEFAULT_COASTLINE:  # D-8: bests are for the standard coastline
        score = round(runstate.state.damage_saved(), 1)
        key = almanac_combo_key()
        best = runstate.almanac["best"].get(key)
        if best is None or score > best["score"]:
            runstate.almanac["best"][key] = {
                "score": score, "seasons": runstate.state.season - 1, "tier": runstate.state.current_tier_index(),
                "rows_dry": runstate.state.rows_dry_count(), "retreat": len(runstate.state.retreat_rows),
                "tourism": runstate.state.diversification["tourism"],
                "aquaculture": runstate.state.diversification["aquaculture"], "heritage": protected,
            }
    if changed:
        _write_local_storage_item(ALMANAC_KEY, json.dumps(runstate.almanac, separators=(",", ":")))


def almanac_best_text(entry):
    parts = [f"tier {TIER_BADGES[entry['tier']]} {ADAPTATION_TIERS[entry['tier']]['name']}"]
    if entry["retreat"]:
        parts.append(f"retreat x{entry['retreat']}")
    if entry["tourism"] or entry["aquaculture"]:
        parts.append(f"tourism {entry['tourism']}, aquaculture {entry['aquaculture']}")
    if entry["heritage"]:
        parts.append(f"{entry['heritage']} heritage site(s)")
    return (
        f"{entry['score']:.0f} damage avoided over {entry['seasons']} seasons, "
        f"{entry['rows_dry']} of {COASTLINE_ROWS} rows dry; " + ", ".join(parts)
    )


def almanac_best_line():
    """D-25: one line for the session summary, from the almanac."""
    entry = runstate.almanac["best"].get(almanac_combo_key())
    lag = "harder lag" if runstate.state.hard_lag_mode else "standard lag"
    if entry is None:
        return ""
    return (
        f"Best for the {runstate.state.sea_scenario} sea with {lag}: {entry['score']:.0f} damage avoided over "
        f"{entry['seasons']} seasons. This session: {runstate.state.damage_saved():.0f} over {max(0, runstate.state.season - 1)}."
    )


def almanac_rows_html():
    rows = []
    for scenario, config in SEA_SCENARIOS.items():
        for lag, lag_label in (("standard", "Standard lag"), ("hard", "Harder lag")):
            key = f"{scenario}|{lag}"
            entry = runstate.almanac["best"].get(key)
            current = " (this session)" if key == almanac_combo_key() else ""
            label = f"{scenario.capitalize()} sea, {lag_label}{current}"
            rows.append(
                f"<tr><th scope=\"row\">{html.escape(label)}</th>"
                f"<td>{html.escape(almanac_best_text(entry)) if entry else 'No run yet'}</td></tr>"
            )
    return "".join(rows)


def render_almanac():
    toggle = document.getElementById("almanac-toggle-button")
    panel = document.getElementById("almanac-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Harbor Almanac" if runstate.almanac_open else "📖 Harbor Almanac"
    panel.hidden = not runstate.almanac_open
    if not runstate.almanac_open:
        return
    lifetime = document.getElementById("almanac-lifetime")
    if lifetime is not None:
        lifetime.innerHTML = "".join(
            f"<li><strong>{runstate.almanac[key]}</strong> {html.escape(label.lower())}</li>"
            for key, label in ALMANAC_LIFETIME
        )
    best = document.getElementById("almanac-best-body")
    if best is not None:
        best.innerHTML = almanac_rows_html()


# ---- D-6 season planner -----------------------------------------------------
planner_plan = [{category: 0 for category in CATEGORIES} for _ in range(PLANNER_MAX_SEASONS)]


def project_plan(plan, length):
    """Runs the staged investments through a COPY of the settlement and returns one dict
    per planned season (plus the starting point first). The real state is never touched."""
    real = runstate.state
    simulated = copy.deepcopy(real)
    runstate.state = simulated
    points = [_planner_point(simulated, 0, 0)]
    try:
        for index in range(max(0, min(int(length), PLANNER_MAX_SEASONS))):
            skipped = 0
            for category in CATEGORIES:
                for _ in range(plan[index].get(category, 0)):
                    if not simulated.invest(category):
                        skipped += 1
            simulated.advance_season()
            points.append(_planner_point(simulated, index + 1, skipped))
    finally:
        runstate.state = real
    return points


def _planner_point(sim, step, skipped):
    at_risk = sum(
        1 for row in range(COASTLINE_ROWS)
        if not sim.row_lost(row) and sim.seasons_until_flood(row) <= PLANNER_RISK_SEASONS
    )
    return {
        "step": step, "season": sim.season, "funds": sim.funds, "acidity": sim.acidity,
        "fish_yield": sim.fish_yield_multiplier(), "rows_dry": sim.rows_dry_count(),
        "rows_at_risk": at_risk, "tier": sim.current_tier_index(), "skipped": skipped,
        "damage": sim.damage_log[-1] if step else 0.0,
    }


def planner_chart_svg(points):
    if len(points) < 2:
        return ""
    step = SPARKLINE_WIDTH / (len(points) - 1)
    acid = _xy([min(1.0, p["acidity"] / FISH_DAMAGE_SCALE) for p in points], step)
    fish = _xy([p["fish_yield"] for p in points], step)
    risk = _xy([p["rows_at_risk"] / COASTLINE_ROWS for p in points], step)
    lines = [
        ("Now" if p["step"] == 0 else f"Planned season {p['step']}")
        + f": acidity {p['acidity']:.1f}, fishing yield {p['fish_yield'] * 100:.0f}%, "
        f"{p['rows_at_risk']} dry row(s) at risk, funds {p['funds']:.0f}"
        for p in points
    ]
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="acidity-fish-sparkline" '
        f'role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Projected acidity (purple), fishing yield (green) and dry rows at risk (amber) '
        f'over the planned seasons. Left and right arrow keys read each season.">'
        f'{_series_svg(acid, "acidity")}{_series_svg(fish, "fish", dash="5 3")}'
        f'{_series_svg(risk, "risk", dash="2 2")}</svg>'
    )


def planner_summary_text(points):
    if len(points) < 2:
        return "Stage some investments to see where they lead."
    last = points[-1]
    skipped = sum(p["skipped"] for p in points)
    text = (
        f"After {len(points) - 1} planned season(s) you would be at Season {last['season']} with "
        f"{last['funds']:.0f} funds, acidity {last['acidity']:.1f}, fishing yield "
        f"{last['fish_yield'] * 100:.0f}%, {last['rows_dry']} of {COASTLINE_ROWS} rows dry and "
        f"{last['rows_at_risk']} of those at risk (flooding within {PLANNER_RISK_SEASONS} seasons)."
    )
    if skipped:
        text += f" {skipped} staged investment(s) were not affordable and were skipped."
    return text + " This is a projection only; nothing has been spent."


def planner_rows_html(points):
    rows = []
    for p in points[1:]:
        flag = f" ({p['skipped']} not affordable)" if p["skipped"] else ""
        rows.append(
            f"<tr><td>{p['season'] - 1}</td><td>{p['funds']:.0f}{flag}</td><td>{p['acidity']:.1f}</td>"
            f"<td>{p['fish_yield'] * 100:.0f}%</td><td>{p['damage']:.0f}</td>"
            f"<td>{p['rows_dry']}</td><td>{p['rows_at_risk']}</td>"
            f"<td>{TIER_BADGES[p['tier']]} {p['tier']}</td></tr>"
        )
    return "".join(rows)


def render_planner():
    toggle = document.getElementById("planner-toggle-button")
    panel = document.getElementById("planner-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Season Planner" if runstate.planner_open else "🧭 Season Planner"
    panel.hidden = not runstate.planner_open
    if not runstate.planner_open:
        return
    length_select = document.getElementById("planner-length")
    if length_select is not None and str(length_select.value) != str(runstate.planner_length):
        length_select.value = str(runstate.planner_length)
    for number in range(1, PLANNER_MAX_SEASONS + 1):
        row = document.getElementById(f"planner-row-{number}")
        if row is not None:
            row.hidden = number > runstate.planner_length
        for category in CATEGORIES:
            field = document.getElementById(f"planner-s{number}-{category}")
            if field is not None and str(field.value) != str(planner_plan[number - 1][category]):
                field.value = str(planner_plan[number - 1][category])
    points = project_plan(planner_plan, runstate.planner_length)
    body = document.getElementById("planner-body")
    if body is not None:
        body.innerHTML = planner_rows_html(points)
    chart = document.getElementById("planner-chart")
    if chart is not None:
        chart.innerHTML = planner_chart_svg(points)
    summary = document.getElementById("planner-summary")
    if summary is not None:
        summary.innerText = planner_summary_text(points)
    commit = document.getElementById("planner-commit-button")
    if commit is not None:
        commit.innerText = f"Commit season {runstate.state.season} (spend and advance)"


def _make_planner_input_handler(number, category):
    def handler(event=None):
        try:
            value = int(float(getattr(getattr(event, "target", None), "value", "")))
        except (TypeError, ValueError):
            value = 0
        planner_plan[number - 1][category] = max(0, min(PLANNER_MAX_PER_CATEGORY, value))
        render_planner()
    return handler
