"""Achievements: the checks, progress readouts, the earned list, the panel and the unlock toast."""

import json
import os

from js import document, setTimeout
from pyodide.ffi import create_proxy

import consulting
import founding
import monuments
import par
import sim
import sustainability

import continuum_runstate as runstate
from continuum_base import SEASON_SECONDS, current_effects


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration exactly. See CLAUDE.md's Milestone 15 build notes for the
# full catalog-design reasoning.
# ===========================================================================
#
# "Derive, don't track" holds for every entry here: every achievement is a
# pure function of state this game already persists (era progress via
# campaign.furthest_era, the full score_history, the research tree's own
# researched list, and the season loop's own last_report ratios) — no new
# tracked state was needed except `campaign.has_revisited` (save.py), added
# via the same five-step defensive pattern SOL's own visited_bodies used
# (safe default, mutated only at the real event, saved, defensive fallback
# on load, no backfill needed here since no pre-existing save could already
# be "mid-revisit but the flag says no").
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()`/Le Champ
    de Mots' `_read_json_asset()`: the boot script fetches achievements.json
    and hands it to Python as a window global before this file runs; the
    pytest harness's fake `js` module has no such attribute, so this falls
    through to reading the file straight off disk."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note: achievements are additive, not core
# gameplay, so a boot-script regression here degrades to "no achievements
# catalog" rather than taking down the whole module import.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

# Branch-depth threshold for the three "Tradition" achievements — roughly
# half of any one branch's ~14-16 nodes (see CLAUDE.md), deep enough to
# mean real, sustained investment in one branch rather than a few early
# freebies.
BRANCH_SPECIALIST_THRESHOLD = 8
EQUITY_CHAMPION_MIN_POPULATION = 25
A_REAL_CITY_POPULATION = 100
# sustainability.components() returns each component on a 0..1 scale, NOT
# the 0..100 scale evaluate()/the UI display (evaluate() multiplies by 100
# for the headline readout) -- a real bug caught by this milestone's own
# test suite before it shipped (both thresholds below were first written as
# 90/85, which no settlement could ever satisfy). Named here, once, so a
# future edit can't reintroduce the same off-by-100 mistake by hand.
EQUITY_CHAMPION_MIN_EQUITY = 0.90
BUILT_TO_LAST_MIN_RESILIENCE = 0.85


def _ever_thriving():
    if runstate.state.peak_score is not None and runstate.state.peak_score >= 85:
        return True
    return sustainability.score(runstate.state, current_effects()) >= 85


def _ever_recovered_from_collapse():
    """True if the score ever fell into Collapsing (<30) and later, at some
    later point in the same history, recovered to Steady or better (>=70).

    Reads state.ever_recovered_from_collapse, a sticky flag CityState.
    record_score() maintains incrementally as each season's score comes in
    — not a scan over score_history itself, which is now capped (Z25) and
    so is no longer guaranteed to hold the whole lifetime history."""
    return runstate.state.ever_recovered_from_collapse


def _era_reached(era):
    # K22: eras a consulting case starts in (or before) were inherited, not
    # reached, so they do not count towards the "reached era" achievements.
    case = consulting.get(runstate.campaign.ui)
    if case is not None and sim.era_index(era) <= sim.era_index(consulting.CASES[case["case"]]["era"]):
        return False
    return sim.era_index(runstate.campaign.furthest_era) >= sim.era_index(era)


def _earned_affinity(branch):
    """Researched nodes in a branch, not counting any a consulting case inherited (K22)."""
    inherited = set(consulting.inherited_for(runstate.campaign))
    return sum(1 for n in runstate.tree.researched if n not in inherited and runstate.tree.nodes[n].branch == branch)


def _full_coordination():
    report = runstate.state.last_report or {}
    return report.get("canals", 0) > 0 and report.get("canal_staffing_ratio", 0.0) >= 1.0


def _nobody_exposed():
    report = runstate.state.last_report or {}
    return report.get("public_works", 0) > 0 and report.get("public_works_coverage_ratio", 0.0) >= 1.0


def _well_supplied_holdings():
    report = runstate.state.last_report or {}
    return report.get("holdings_residents", 0) > 0 and report.get("outlying_served", 0.0) >= 1.0


def _well_designed_rings():
    report = runstate.state.last_report or {}
    return report.get("habitat_rings", 0) > 0 and report.get("habitat_layout_ratio", 0.0) >= 1.0


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is cached or hand-flagged, matching SOL's own discipline.
ACHIEVEMENT_CHECKS = {
    "reached_agrarian": lambda: _era_reached("agrarian"),
    "reached_classical": lambda: _era_reached("classical"),
    "reached_medieval": lambda: _era_reached("medieval"),
    "reached_industrial": lambda: _era_reached("industrial"),
    "reached_digital": lambda: _era_reached("digital"),
    "reached_space": lambda: _era_reached("space"),
    "reached_relay": lambda: _era_reached("relay"),
    "thriving_once": _ever_thriving,
    "phoenix_settlement": _ever_recovered_from_collapse,
    "provision_specialist": lambda: _earned_affinity("provision") >= BRANCH_SPECIALIST_THRESHOLD,
    "community_specialist": lambda: _earned_affinity("community") >= BRANCH_SPECIALIST_THRESHOLD,
    "craft_specialist": lambda: _earned_affinity("craft") >= BRANCH_SPECIALIST_THRESHOLD,
    "root_and_branch": lambda: len(runstate.tree.researched) >= len(runstate.tree.nodes),
    "equity_champion": lambda: (
        runstate.state.population >= EQUITY_CHAMPION_MIN_POPULATION
        and sustainability.components(runstate.state, current_effects())["equity"] >= EQUITY_CHAMPION_MIN_EQUITY
    ),
    "built_to_last": lambda: (
        sustainability.components(runstate.state, current_effects())["resilience"] >= BUILT_TO_LAST_MIN_RESILIENCE
    ),
    "full_coordination": _full_coordination,
    "nobody_exposed": _nobody_exposed,
    "well_designed_rings": _well_designed_rings,
    "well_supplied_holdings": _well_supplied_holdings,
    "a_real_city": lambda: runstate.state.population >= A_REAL_CITY_POPULATION,
    "looking_back": lambda: runstate.campaign.has_revisited,
    # K-26: the par-time badges, from the result stored on entering the last era.
    "par_seasons": lambda: par.seasons_earned(par.get(runstate.campaign.ui)),
    "par_time": lambda: par.time_earned(par.get(runstate.campaign.ui), SEASON_SECONDS),
}

# Progress readouts, only for achievements with a natural numeric scale-up —
# a plain earned/not-yet is the honest shape for the rest (era-reached,
# phoenix, the coordination/coverage achievements are all one-shot).
ACHIEVEMENT_PROGRESS = {
    "provision_specialist": lambda: (_earned_affinity("provision"), BRANCH_SPECIALIST_THRESHOLD),
    "community_specialist": lambda: (_earned_affinity("community"), BRANCH_SPECIALIST_THRESHOLD),
    "craft_specialist": lambda: (_earned_affinity("craft"), BRANCH_SPECIALIST_THRESHOLD),
    "root_and_branch": lambda: (len(runstate.tree.researched), len(runstate.tree.nodes)),
    "a_real_city": lambda: (runstate.state.population, A_REAL_CITY_POPULATION),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input (see get_state() below)."""
    # O-5: badges earned in an earlier settlement (kept in campaign.ui by
    # founding.found_new) stay earned; the live checks add this settlement's.
    if runstate.sandbox_active:  # Z-18: nothing in the sandbox earns anything; the real list is shown as it was
        return list(runstate._sandbox_real["earned"])
    before = set(founding.earned_before(runstate.campaign.ui, [entry["id"] for entry in ACHIEVEMENTS]))
    return [entry["id"] for entry in ACHIEVEMENTS if entry["id"] in before or ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each annotated with earned status and
    (where one exists) a live progress readout."""
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


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    # K-31: a "monument row": each card stands on a plinth with a drawn monument
    # for its era, laid out era by era. Order is chronological, then catalog order.
    ordered = sorted(
        enumerate(achievements_summary()),
        key=lambda pair: monuments.sort_key(pair[1]["id"], pair[0]),
    )
    for _index, entry in ordered:
        kind = monuments.kind_of(entry["id"])
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]

        icon = document.createElement("div")
        icon.className = "monument-icon"
        icon.setAttribute("aria-hidden", "true")
        icon.innerHTML = monuments.icon_svg(kind, entry["earned"])
        card.appendChild(icon)

        era_caption = document.createElement("p")
        era_caption.className = "monument-caption"
        era_caption.innerText = monuments.caption(kind)
        card.appendChild(era_caption)

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        state_text = document.createElement("p")
        state_text.className = "monument-state"
        state_text.innerText = "Earned" if entry["earned"] else "Not yet earned"
        card.appendChild(state_text)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # Hub-dashboard link (ACHIEVEMENTS-SYSTEM-DESIGN.md §5) — signed-in
    # players can see Continuum's progress alongside every other game's
    # there. Relative path, no leading "/" (site-level milestone 7's
    # GitHub Pages subpath fix), rebuilt each open since the panel is
    # cleared first.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
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


# --- unlock toast ---------------------------------------------------------


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())


def _display_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after render() from every action handler that could plausibly
    newly earn an achievement (assign/unassign/build/research/season
    advance/era transition/enter revisit) — never from render() itself, for
    the same reason _seed_achievement_toast_baseline() above exists."""
    if runstate.sandbox_active:  # Z-18: no unlock toasts in the sandbox
        return
    earned_now = set(achievement_ids_earned())
    newly = earned_now - runstate._achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    runstate._achievements_seen_ids = earned_now
