"""Achievement checks and progress tables, the achievements summary and panel, full-completion tracking."""

import math

from js import document

import sol_runstate as runstate
from sol_charter import CHARTER_MEMBER_STAMPS, mission_stamps
from sol_codex import CLUES, codex_found
from sol_observatory import CHART, COMETS_TO_CATCH, point_state, revealed_points
from sol_rhythm import CHAINS, IN_RHYTHM_STREAK, chains_found
from sol_rules import GAS_GIANT_BODIES, PLANETS, RESEARCH_TIERS, TICK_INTERVAL_MS, planet_state
from sol_runmods import ANOMALIES, anomalies_seen
from sol_scarcity import scarcity_days
from sol_story import ACHIEVEMENTS
from sol_util import _format_duration, _terraformed_planet_count, _total_trade_routes


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the reference
# integration for the hub-wide achievements framework.
# ===========================================================================

RESOURCE_BARON_THRESHOLD = 1_000_000
ECOLOGICAL_BALANCE_MIN_HEALTH = 95.0
TRADE_NETWORK_MIN_ROUTES = 5
PLANETARY_RENAISSANCE_MIN_TERRAFORMED = 4


def _max_single_resource():
    return max((state["resource_count"] for state in planet_state.values()), default=0.0)


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged. "Earth" counts as always
# unlocked and always visited from the start (see PLANETS/visited_bodies
# above), so every len(PLANETS)-based target below is expressed relative to
# that the same way update_cross_summary() already treats Earth as a given.
ACHIEVEMENT_CHECKS = {
    "first_ore": lambda: planet_state["Earth"]["resource_count"] >= 1,
    "automated": lambda: planet_state["Earth"]["generator_count"] >= 1,
    "recycler_online": lambda: any(state["recycler_count"] >= 1 for state in planet_state.values()),
    "off_world": lambda: len(runstate.visited_bodies) >= 2,
    "trade_route_established": lambda: any(state["trade_routes"] for state in planet_state.values()),
    "tier_one_cleared": lambda: runstate.completed_tiers >= 1,
    "solar_system_unlocked": lambda: len(runstate.unlocked_bodies) >= len(PLANETS) - 1,
    "tier_two_cleared": lambda: runstate.completed_tiers >= len(RESEARCH_TIERS),
    "grand_tour": lambda: len(runstate.visited_bodies) >= len(PLANETS),
    "governor_appointed": lambda: runstate.governor_purchase_count >= 1,
    "sky_city_founder": lambda: any(
        planet_state[p].get("sky_city_count", 0) >= 1 for p in GAS_GIANT_BODIES
    ),
    "trade_network": lambda: _total_trade_routes() >= TRADE_NETWORK_MIN_ROUTES,
    "ecological_balance": lambda: any(
        state["generator_count"] >= 1 and state["ecology_health"] >= ECOLOGICAL_BALANCE_MIN_HEALTH
        for state in planet_state.values()
    ),
    "resource_baron": lambda: _max_single_resource() >= RESOURCE_BARON_THRESHOLD,
    "terraformer": lambda: _terraformed_planet_count() >= 1,
    "eight_economies": lambda: all(state["generator_count"] >= 1 for state in planet_state.values()),
    "planetary_renaissance": lambda: _terraformed_planet_count() >= PLANETARY_RENAISSANCE_MIN_TERRAFORMED,
    "full_system_terraformed": lambda: _terraformed_planet_count() >= len(PLANETS),
    # Second achievement wave (A2/A13) -- all four are one-shot historical
    # flags (module-level globals near total_ticks/any_generator_ever_built
    # above), not live-derived from current state, because "within N
    # minutes" and "before a generator ever existed" both describe
    # something about PLAY HISTORY a live check can't reconstruct after
    # the fact (see that block's own comment for the full reasoning).
    "quick_start": lambda: runstate.quick_start_hit,
    "swift_expansion": lambda: runstate.swift_expansion_hit,
    "manual_labor": lambda: runstate.manual_labor_hit,
    "off_the_grid": lambda: runstate.off_the_grid_hit,
    # A19: "close call" family. One-shot historical flags for the same reason
    # as the wave above: "fell to near zero and recovered" is play history.
    "close_call": lambda: runstate.close_call_hit,
    "back_from_the_brink": lambda: runstate.back_from_brink_hit,
    # Round-3 batch: both are lifetime records, so a prestige never un-earns them.
    "in_rhythm": lambda: runstate.best_click_streak >= IN_RHYTHM_STREAK,
    "chain_reactor": lambda: chains_found() >= len(CHAINS),
    # Round-4 batch: all four are lifetime collections, so a prestige never un-earns them.
    "codex_keeper": lambda: len(codex_found) >= len(CLUES),
    "weather_watcher": lambda: len(anomalies_seen) >= len(ANOMALIES),
    "charter_member": lambda: len(mission_stamps) >= CHARTER_MEMBER_STAMPS,
    "great_works": lambda: runstate.megaprojects_all_ever,
    # Round-5 batch: both are lifetime collections.
    "star_cartographer": lambda: runstate.chart_revealed >= len(CHART),
    "comet_catcher": lambda: runstate.comets_caught_total >= COMETS_TO_CATCH,
    "relay_network": lambda: len(revealed_points()) == 4 and all(
        point_state(e["id"]) in ("yours", "partner") for e in revealed_points()),
    # Round-6 batch: all three are lifetime records kept per date, so a prestige never un-earns them.
    "scarcity_survivor": lambda: len(scarcity_days) >= 1,
    "outplayed_governor": lambda: any(r.get("under_par") for r in scarcity_days.values()),
    "seven_scarce_days": lambda: len(scarcity_days) >= SCARCITY_DAYS_FOR_ACHIEVEMENT,
}

# Progress readouts, only for achievements with a natural numeric scale-up —
# a plain earned/not-yet is the honest shape for the rest, rather than
# inventing fractional progress for a one-shot milestone like "build your
# first Recycler somewhere".
SCARCITY_DAYS_FOR_ACHIEVEMENT = 7
ACHIEVEMENT_PROGRESS = {
    "seven_scarce_days": lambda: (min(len(scarcity_days), SCARCITY_DAYS_FOR_ACHIEVEMENT), SCARCITY_DAYS_FOR_ACHIEVEMENT),
    "solar_system_unlocked": lambda: (len(runstate.unlocked_bodies), len(PLANETS) - 1),
    "grand_tour": lambda: (len(runstate.visited_bodies), len(PLANETS)),
    "tier_two_cleared": lambda: (runstate.completed_tiers, len(RESEARCH_TIERS)),
    "trade_network": lambda: (_total_trade_routes(), TRADE_NETWORK_MIN_ROUTES),
    "resource_baron": lambda: (math.floor(_max_single_resource()), RESOURCE_BARON_THRESHOLD),
    "planetary_renaissance": lambda: (_terraformed_planet_count(), PLANETARY_RENAISSANCE_MIN_TERRAFORMED),
    "full_system_terraformed": lambda: (_terraformed_planet_count(), len(PLANETS)),
    "in_rhythm": lambda: (min(runstate.best_click_streak, IN_RHYTHM_STREAK), IN_RHYTHM_STREAK),
    "chain_reactor": lambda: (chains_found(), len(CHAINS)),
    "codex_keeper": lambda: (len(codex_found), len(CLUES)),
    "weather_watcher": lambda: (len(anomalies_seen), len(ANOMALIES)),
    "charter_member": lambda: (min(len(mission_stamps), CHARTER_MEMBER_STAMPS), CHARTER_MEMBER_STAMPS),
    "star_cartographer": lambda: (runstate.chart_revealed, len(CHART)),
    "comet_catcher": lambda: (min(runstate.comets_caught_total, COMETS_TO_CATCH), COMETS_TO_CATCH),
    "relay_network": lambda: (sum(1 for e in revealed_points() if point_state(e["id"]) in ("yours", "partner")), 4),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout — the
    shape the in-game panel wants without re-deriving it from ACHIEVEMENTS +
    ACHIEVEMENT_CHECKS + ACHIEVEMENT_PROGRESS itself."""
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


def best_run_text():
    """R-10: the personal-best playthrough line for the stats panel."""
    if runstate.best_run_ticks is None:
        return "not yet (terraform every world to set it)"
    return _format_duration(runstate.best_run_ticks * (TICK_INTERVAL_MS / 1000))


# --- A-31: trophy shelf ------------------------------------------------------
TROPHY_SHELF_SIZE = 5
TROPHY_HISTORY_MAX = 12
TROPHY_GLYPHS = ["🥇", "🏅", "⭐", "🌟", "🪐", "🚀", "☄️", "🛰️"]
recent_trophies = []  # achievement ids, oldest first


def _trophy_ids_for_shelf():
    earned = set(achievement_ids_earned())
    return [aid for aid in reversed(recent_trophies) if aid in earned][:TROPHY_SHELF_SIZE]


def render_trophy_shelf():
    shelf = document.getElementById("trophy-shelf")
    shown = _trophy_ids_for_shelf()
    shelf.hidden = not shown
    shelf.innerHTML = ""
    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    index_of = {entry["id"]: i for i, entry in enumerate(ACHIEVEMENTS)}
    for aid in shown:
        entry = by_id[aid]
        badge = document.createElement("span")
        badge.className = "trophy-badge" + (" trophy-badge--new" if aid == runstate._trophy_fresh_id else "")
        badge.setAttribute("role", "listitem")
        badge.title = entry["description"]
        glyph = document.createElement("span")
        glyph.className = "trophy-glyph"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = TROPHY_GLYPHS[index_of[aid] % len(TROPHY_GLYPHS)]
        badge.appendChild(glyph)
        label = document.createElement("span")
        label.className = "trophy-label"
        label.innerText = entry["label"]
        badge.appendChild(label)
        shelf.appendChild(badge)


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
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # Retrofit: a link out to the hub-wide achievements dashboard
    # (root index.html's #account-achievements-dashboard, ACHIEVEMENTS-
    # SYSTEM-DESIGN.md §5) — signed-in players can see SOL's progress
    # alongside every other game's there. Relative path, no leading "/"
    # (site-level milestone 7's GitHub Pages subpath fix), rebuilt each
    # open alongside the cards since the whole panel is cleared first.
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
