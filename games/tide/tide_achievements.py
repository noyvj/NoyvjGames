"""Achievements and ranks: catalog, checks, progress, panel, toast."""

import json
import math

from js import document, setTimeout
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_coasts import flooded_row_count, heritage_sites
from tide_rules import (
    ADAPTATION_TIERS, CATEGORIES, CITIZEN_SCIENCE_FACTS, COASTLINE_ROWS, DIVERSIFY_MAX_LEVEL,
    RETREAT_MAX_STEPS,
)


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the
# reference integration for the hub-wide achievements framework; this is
# Tide's own catalog, grounded in its actual mechanics (the three
# investment categories, the adaptation tech tree, the delayed fish-stock
# crash, and the coastline's own flood progression) rather than generic
# filler.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that
# already exists elsewhere on `state`, recomputed fresh on every call —
# never a separately hand-maintained "earned" flag ("derive, don't
# track"). Four checks genuinely needed new tracked state (min_fish_yield_
# ever, max_acidity_ever, max_funds_ever, fortified_in_time_earned — see
# SettlementState.__init__) because the thing they measure ("how far did
# this ever go", "did this happen before that") isn't recoverable from a
# field that only reflects the current moment. Every other check below
# reads state.capacity/state.season/coastline math directly.
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract SOL's game.py established: the page's boot
    script fetches achievements.json and hands it to Python as a window
    global before this file runs; the pytest harness's fake `js` module
    simply has no such attribute, so this falls through to reading the
    file straight off disk, which keeps the module importable outside a
    real browser."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note on this pattern: the real Pyodide runtime
# executes this file's fetched text via `pyodide.runPythonAsync(code)`,
# which never defines `__file__` -- if the window-global read ever comes
# back empty, the filesystem fallback would crash with a bare NameError
# that takes down this entire module import. Achievements are additive,
# not core to Tide's own gameplay, so this degrades to "no achievements
# catalog" instead.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

LOSING_GROUND_ROW_FRACTION = 0.5
TURNING_THE_TIDE_DROP = 20.0
FLUSH_COFFERS_THRESHOLD = 1000.0
TIME_BOUGHT_THRESHOLD = 100.0
THE_LONG_HAUL_SEASON = 20
WELL_ROUNDED_CAPACITY = 5
STOCKS_REBOUND_CRASH_THRESHOLD = 0.7
STOCKS_REBOUND_RECOVERY_THRESHOLD = 0.9


# D-10: Bronze / Silver / Gold ranks. Every rank is its own flat achievement id (storm_bronze, storm_silver,
# storm_gold, ...), so the hub's `achievements_earned` stays a plain list of ids and a dashboard that has never heard
# of ranks still counts them. The extra "family" and "rank" fields in achievements.json are only for this game's panel.
# All six families are derived from state that never goes backwards, so a rank cannot un-earn itself.
RANK_NAMES = ("bronze", "silver", "gold")
RANK_STORMS_WEATHERED = (1, 3)          # bronze, silver; gold is RANK_STORMS_CLEAN clean storms
RANK_STORMS_CLEAN = 3
RANK_HERITAGE_GOLD_SEASON = 15
RANK_MONITOR_REPORTS = (1, 4, len(CITIZEN_SCIENCE_FACTS))
RANK_POPULATION = (110, 120, 130)


def _max_tier_index():
    return len(ADAPTATION_TIERS) - 1


def _all_heritage_protected():
    return runstate.state.protected_heritage_count() >= len(heritage_sites())


ACHIEVEMENT_CHECKS = {
    "underway": lambda: runstate.state.season >= 2,
    "first_output": lambda: runstate.state.capacity["output"] >= 1,
    "first_reduction": lambda: runstate.state.capacity["reduction"] >= 1,
    "first_adaptation": lambda: runstate.state.capacity["adaptation"] >= 1,
    "tier_sandbags": lambda: runstate.state.current_tier_index() >= 1,
    "tier_seawalls": lambda: runstate.state.current_tier_index() >= 2,
    "tier_reinforced": lambda: runstate.state.current_tier_index() >= 3,
    "tier_storm_surge": lambda: runstate.state.current_tier_index() >= _max_tier_index(),
    "first_flood": lambda: flooded_row_count(runstate.state.sea_level) >= 1,
    "losing_ground": lambda: (
        flooded_row_count(runstate.state.sea_level) >= math.ceil(COASTLINE_ROWS * LOSING_GROUND_ROW_FRACTION)
    ),
    "fully_submerged": lambda: flooded_row_count(runstate.state.sea_level) >= COASTLINE_ROWS,
    "the_lag_arrives": lambda: runstate.state.min_fish_yield_ever <= 0.5,
    "stocks_rebound": lambda: (
        runstate.state.min_fish_yield_ever < STOCKS_REBOUND_CRASH_THRESHOLD
        and runstate.state.fish_yield_multiplier() >= STOCKS_REBOUND_RECOVERY_THRESHOLD
    ),
    "turning_the_tide": lambda: (runstate.state.max_acidity_ever - runstate.state.acidity) >= TURNING_THE_TIDE_DROP,
    "flush_coffers": lambda: runstate.state.max_funds_ever >= FLUSH_COFFERS_THRESHOLD,
    "time_bought": lambda: runstate.state.damage_saved() >= TIME_BOUGHT_THRESHOLD,
    "the_long_haul": lambda: runstate.state.season >= THE_LONG_HAUL_SEASON,
    "bending_the_curve": lambda: runstate.state.trend_flattening_announced,
    "well_rounded": lambda: all(
        runstate.state.capacity[category] >= WELL_ROUNDED_CAPACITY for category in CATEGORIES
    ),
    "fortified_in_time": lambda: runstate.state.fortified_in_time_earned,
    # D-10 ranks
    "storm_bronze": lambda: runstate.state.storms_weathered >= RANK_STORMS_WEATHERED[0],
    "storm_silver": lambda: runstate.state.storms_weathered >= RANK_STORMS_WEATHERED[1],
    "storm_gold": lambda: runstate.state.storms_clean >= RANK_STORMS_CLEAN,
    "heritage_bronze": lambda: runstate.state.protected_heritage_count() >= 1,
    "heritage_silver": lambda: _all_heritage_protected(),
    "heritage_gold": lambda: _all_heritage_protected() and runstate.state.season >= RANK_HERITAGE_GOLD_SEASON,
    "retreat_bronze": lambda: len(runstate.state.retreat_rows) >= 1,
    "retreat_silver": lambda: len(runstate.state.retreat_rows) >= RETREAT_MAX_STEPS,
    "retreat_gold": lambda: runstate.state.early_retreats >= RETREAT_MAX_STEPS,
    "diversify_bronze": lambda: max(runstate.state.diversification.values()) >= 1,
    "diversify_silver": lambda: max(runstate.state.diversification.values()) >= DIVERSIFY_MAX_LEVEL,
    "diversify_gold": lambda: min(runstate.state.diversification.values()) >= DIVERSIFY_MAX_LEVEL,
    "monitor_bronze": lambda: runstate.state.monitoring_reports >= RANK_MONITOR_REPORTS[0],
    "monitor_silver": lambda: runstate.state.monitoring_reports >= RANK_MONITOR_REPORTS[1],
    "monitor_gold": lambda: runstate.state.monitoring_reports >= RANK_MONITOR_REPORTS[2],
    "population_bronze": lambda: runstate.state.peak_population >= RANK_POPULATION[0],
    "population_silver": lambda: runstate.state.peak_population >= RANK_POPULATION[1],
    "population_gold": lambda: runstate.state.peak_population >= RANK_POPULATION[2],
}

# Progress readouts, only for achievements with a natural numeric
# scale-up — a plain earned/not-yet is the honest shape for the rest
# (one-shot milestones like "invest in Output for the first time" don't
# get a fake "0 of 1").
ACHIEVEMENT_PROGRESS = {
    "losing_ground": lambda: (
        flooded_row_count(runstate.state.sea_level),
        math.ceil(COASTLINE_ROWS * LOSING_GROUND_ROW_FRACTION),
    ),
    "fully_submerged": lambda: (flooded_row_count(runstate.state.sea_level), COASTLINE_ROWS),
    "flush_coffers": lambda: (int(runstate.state.max_funds_ever), int(FLUSH_COFFERS_THRESHOLD)),
    "time_bought": lambda: (int(runstate.state.damage_saved()), int(TIME_BOUGHT_THRESHOLD)),
    "the_long_haul": lambda: (runstate.state.season, THE_LONG_HAUL_SEASON),
    "well_rounded": lambda: (
        min(runstate.state.capacity[category] for category in CATEGORIES),
        WELL_ROUNDED_CAPACITY,
    ),
    # D-10 ranks: how far along each one is
    "storm_bronze": lambda: (runstate.state.storms_weathered, RANK_STORMS_WEATHERED[0]),
    "storm_silver": lambda: (runstate.state.storms_weathered, RANK_STORMS_WEATHERED[1]),
    "storm_gold": lambda: (runstate.state.storms_clean, RANK_STORMS_CLEAN),
    "heritage_silver": lambda: (runstate.state.protected_heritage_count(), len(heritage_sites())),
    "heritage_gold": lambda: (min(runstate.state.season, RANK_HERITAGE_GOLD_SEASON) if _all_heritage_protected() else 0,
                              RANK_HERITAGE_GOLD_SEASON),
    "retreat_silver": lambda: (len(runstate.state.retreat_rows), RETREAT_MAX_STEPS),
    "retreat_gold": lambda: (runstate.state.early_retreats, RETREAT_MAX_STEPS),
    "diversify_silver": lambda: (max(runstate.state.diversification.values()), DIVERSIFY_MAX_LEVEL),
    "diversify_gold": lambda: (sum(runstate.state.diversification.values()), 2 * DIVERSIFY_MAX_LEVEL),
    "monitor_silver": lambda: (runstate.state.monitoring_reports, RANK_MONITOR_REPORTS[1]),
    "monitor_gold": lambda: (runstate.state.monitoring_reports, RANK_MONITOR_REPORTS[2]),
    "population_bronze": lambda: (runstate.state.peak_population, RANK_POPULATION[0]),
    "population_silver": lambda: (runstate.state.peak_population, RANK_POPULATION[1]),
    "population_gold": lambda: (runstate.state.peak_population, RANK_POPULATION[2]),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


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
                "family": entry.get("family", ""),  # D-10
                "rank": entry.get("rank", ""),
            }
        )
    return summary


def rank_summary():
    """D-10: one line per ranked family: the best rank earned and how many of its three are done."""
    earned = set(achievement_ids_earned())
    families = {}
    for entry in ACHIEVEMENTS:
        family = entry.get("family")
        if not family:
            continue
        label = entry["label"].split(":")[0]
        row = families.setdefault(family, {"family": family, "label": label, "best": "", "done": 0, "total": 0})
        row["total"] += 1
        if entry["id"] in earned:
            row["done"] += 1
            row["best"] = entry.get("rank", "")
    return list(families.values())


_toast_hide_proxy = None

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    return set(achievement_ids_earned())


def show_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")
    toast.classList.add("achievement-toast--ripple")  # D-31: a brief ripple (CSS stops it under reduced motion)

    # Never destroy a still-pending timer's proxy: the browser would later
    # call it and Pyodide throws "Object has already been destroyed". Each
    # timer owns its own proxy and destroys it after firing; a newer toast
    # just bumps the generation so stale timers become no-ops.
    runstate._toast_hide_proxy_gen += 1
    my_gen = runstate._toast_hide_proxy_gen
    holder = []

    def _hide():
        if my_gen == runstate._toast_hide_proxy_gen:
            toast.classList.remove("achievement-toast--visible")
            toast.classList.remove("achievement-toast--ripple")
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], ACHIEVEMENT_TOAST_DURATION_MS)


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass, e.g. an Advance Season click that both
    unlocks a tier and crashes fish yield)."""
    current = _earned_snapshot()
    newly_earned_ids = current - runstate._previously_earned_ids
    runstate._previously_earned_ids = current
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if not newly_earned:
        return
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


RANK_MEDALS = {"bronze": "\U0001F949", "silver": "\U0001F948", "gold": "\U0001F947"}  # D-10
ACHIEVEMENT_GLYPH_EARNED = "\U0001FAB8"  # coral
ACHIEVEMENT_GLYPH_LOCKED = "\u3030\ufe0f"  # a wave outline


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    if toggle is None or panel is None:
        return
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"\U0001F3C6 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    ranks = [row for row in rank_summary() if row["total"]]
    if ranks:  # D-10: the ranked families at a glance
        line = document.createElement("p")
        line.className = "achievement-rank-summary"
        line.innerText = "Ranks: " + "; ".join(
            f"{row['label']} {row['best'].capitalize() if row['best'] else 'none yet'} ({row['done']}/{row['total']})"
            for row in ranks
        )
        panel.appendChild(line)
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = (
            "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        )
        card.dataset.achievementId = entry["id"]
        if entry["rank"]:  # D-10: a rank is spelled out in words and by a medal, never by colour alone
            card.className += f" achievement-card--rank achievement-card--rank-{entry['rank']}"
            card.dataset.achievementRank = entry["rank"]

        glyph = document.createElement("span")  # D-31: a coral for each earned badge, a hollow wave while locked
        glyph.className = "achievement-card-glyph" if entry["earned"] else "achievement-card-glyph achievement-card-glyph--locked"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = ACHIEVEMENT_GLYPH_EARNED if entry["earned"] else ACHIEVEMENT_GLYPH_LOCKED
        card.appendChild(glyph)

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"\U0001F3C6 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if entry["rank"]:
            tag = document.createElement("p")
            tag.className = "achievement-card-rank"
            tag.innerText = f"{RANK_MEDALS[entry['rank']]} {entry['rank'].capitalize()} rank"
            card.appendChild(tag)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    hub_link = document.createElement("a")
    hub_link.className = "achievements-hub-link"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()
