"""Achievements (catalog, checks, progress, toast), the changelog panel and the ribbon flourish."""

import json

from js import document, setTimeout
from pyodide.ffi import create_proxy

import trade_runstate as runstate
from trade_blueprints import blueprints
from trade_captains import CAPTAINS
from trade_cartel import CARTEL_ACHIEVEMENT_MOVES
from trade_chain_logic import chain_medal_for
from trade_chain_rules import CHAIN_BY_ID, CHAIN_GOLD_ACHIEVEMENT, CHAIN_PUZZLES
from trade_charter import CHARTER_VETERAN_COUNT, background_world_count
from trade_colony import (
    colony_states, galaxy_expansion_unlocked, outer_reaches_unlocked, umbral_reach_unlocked,
)
from trade_crises import CRISIS_IDS
from trade_exchange import EXCHANGE_MARKET_MAKER_FILLS
from trade_expedition import CURIO_IDS
from trade_market import market_crash_ever, market_multiplier
from trade_meridian import MERIDIAN_ANSWER_ACHIEVEMENT
from trade_records import records
from trade_research import RESEARCH_NODES, max_automated_ships
from trade_rules import (
    COLONIES, ENDGAME_BACKGROUND_WORLD_CAP, ENERGY, EXPANSION_COLONIES, GRAIN, MACHINERY, ORE, WATER,
)
from trade_ships import MARKET_RECOVERY_THRESHOLD, automated_ship_count, ships
from trade_uikit import _effects_on
from trade_weather import WEATHER_ACHIEVEMENT_EVENTS


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the
# reference integration for the hub-wide achievements framework; this is
# Trade Empire's own catalog, grounded in its actual mechanics (sales,
# automation, fleet priority, research, colony development, market crashes,
# the multi-system endgame) rather than generic filler.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that
# already exists elsewhere in this module, recomputed fresh on every call
# — never a separately hand-maintained "earned" flag. A handful of checks
# genuinely needed new tracked state (see the module-level declarations
# above `total_sales_count` through `market_crash_ever`) because the thing
# they measure ("this ever happened") isn't recoverable from state that
# only reflects the *current* moment — e.g. total_profit can go back down
# after an automation purchase, so it alone can't answer "has this session
# ever reached 100,000 profit."
ACHIEVEMENTS_FILENAME = "achievements.json"

HOME_SYSTEM_GOODS = frozenset({ORE, GRAIN, MACHINERY, WATER, ENERGY})


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
# which never defines `__file__` the way a normal file-based import does —
# if `_read_achievements_json()`'s window-global read ever comes back
# empty, its filesystem fallback would crash with a bare NameError that
# takes down this entire module import, not just achievements. Achievements
# are additive, not core to Trade Empire's own gameplay, so this degrades
# to "no achievements catalog" instead.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []


# ===========================================================================
# Changelog panel (site-wide goal, planning/TODO.md, origin K16: "Per-game
# in-game changelog panel, for every game"). A quick highlights view, not a
# full duplicate of CLAUDE.md/BCM114-DEV-LOG.md -- same loading contract as
# ACHIEVEMENTS above, except CHANGELOG is a flat list (no wrapping key) --
# see changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as `_read_achievements_json()` above."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to
# Trade Empire's own gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
    CHANGELOG = []


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "\U0001F4CB What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        card = document.createElement("div")
        card.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-date"
        date.innerText = entry["date"]
        card.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-text"
        text.innerText = entry["entry"]
        card.appendChild(text)

        panel.appendChild(card)


PROFIT_10K_THRESHOLD = 10000
PROFIT_100K_THRESHOLD = 100000


def _all_research_unlocked():
    # J15: the two specialization branches exclude each other, so "all
    # research" means every shared node plus a completed branch (either).
    shared = {node_id for node_id, node in RESEARCH_NODES.items() if not node.get("excludes")}
    completed_branch = "auto_efficiency_2" in runstate.unlocked_research or "market_insight_2" in runstate.unlocked_research
    return shared <= runstate.unlocked_research and completed_branch


def _any_colony_developed():
    return any(state.is_developed() for state in colony_states.values())


def _home_system_fully_developed():
    return all(colony_states[cid].is_developed() for cid in COLONIES)


def _any_kepler_colony_developed():
    return any(
        colony_states[cid].is_developed() for cid in EXPANSION_COLONIES if cid in colony_states
    )


def _market_recovered_from_a_crash():
    return any(
        crashed and market_multiplier[good] >= MARKET_RECOVERY_THRESHOLD
        for good, crashed in market_crash_ever.items()
    )


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_sale": lambda: runstate.total_sales_count >= 1,
    "first_automation": lambda: automated_ship_count() >= 1,
    "automation_slots_maxed": lambda: automated_ship_count() >= max_automated_ships(),
    "fleet_priority_enabled": lambda: runstate.fleet_priority_enabled,
    "fleet_priority_reposition": lambda: runstate.ever_repositioned,
    "fast_ships_researched": lambda: "fast_ships" in runstate.unlocked_research,
    "hauler_researched": lambda: "hauler" in runstate.unlocked_research,
    "automation_slot_researched": lambda: "automation_slot" in runstate.unlocked_research,
    "all_research_unlocked": _all_research_unlocked,
    "galaxy_expansion_unlocked": galaxy_expansion_unlocked,
    "colony_developed": _any_colony_developed,
    "home_system_fully_developed": _home_system_fully_developed,
    "kepler_colony_developed": _any_kepler_colony_developed,
    "profit_10k": lambda: runstate.max_profit_ever >= PROFIT_10K_THRESHOLD,
    "profit_100k": lambda: runstate.max_profit_ever >= PROFIT_100K_THRESHOLD,
    "diversified_trader": lambda: HOME_SYSTEM_GOODS <= runstate.goods_sold_ever,
    "market_recovery": _market_recovered_from_a_crash,
    "endgame_reached": lambda: runstate.endgame_reached,
    "new_corporation": lambda: runstate.legacy_level >= 1,
    # O-1/O-4: derived from state that survives a renewal, so nothing needs carrying.
    "charter_perk": lambda: len(runstate.charter_perks) >= 1,
    "charter_veteran": lambda: runstate.charters_completed >= CHARTER_VETERAN_COUNT,
    "hard_charter_done": lambda: runstate.ledger_hard_completed >= 1,
    # J-7: derived from captains_met, which survives a renewal.
    "captains_table": lambda: len(runstate.captains_met) >= 1,
    "full_roster": lambda: len(runstate.captains_met) >= len(CAPTAINS),
    "guild_partner": lambda: runstate.guild_completed >= 1,
    "guild_favorite": lambda: runstate.guild_completed >= 5,
    "background_galaxy_maxed": lambda: background_world_count() >= ENDGAME_BACKGROUND_WORLD_CAP,
    "dark_run": lambda: records["dark_runs"] >= 1,  # J-30
    "storm_watcher": lambda: records["weather_events"] >= WEATHER_ACHIEVEMENT_EVENTS,  # J-17
    "first_expedition": lambda: records["expeditions"] >= 1,  # J-23
    "first_fill": lambda: records["exchange_fills"] >= 1,  # J-27
    "hull_designer": lambda: len(blueprints) >= 1,  # J-19
    "first_hub": lambda: records["hubs_set"] >= 1,  # J-21
    "crisis_averted": lambda: bool(records["crisis_best"]),  # J-9
    "gold_standard": lambda: all(records["crisis_best"].get(c, {}).get("medal") == "gold" for c in CRISIS_IDS),
    "rival_answered": lambda: records["meridian_answers"] >= MERIDIAN_ANSWER_ACHIEVEMENT,  # J-11
    "board_member": lambda: records["cartel_moves"] >= CARTEL_ACHIEVEMENT_MOVES,  # J-3
    "custom_fleet": lambda: any(ship.hull is not None for ship in ships.values()),
    "market_maker": lambda: records["exchange_fills"] >= EXCHANGE_MARKET_MAKER_FILLS,
    "curio_cabinet": lambda: len(records["curios"]) >= len(CURIO_IDS),
    "chain_first": lambda: bool(records["chain_best"]),  # J-5
    "chain_par": lambda: _chain_gold_count() >= CHAIN_GOLD_ACHIEVEMENT,
    "chain_shared": lambda: _chain_chapter_solved(3) >= _chain_chapter_size(3),
    "chain_master": lambda: len(records["chain_best"]) >= len(CHAIN_PUZZLES),
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for the rest.
ACHIEVEMENT_PROGRESS = {
    "profit_10k": lambda: (int(runstate.max_profit_ever), PROFIT_10K_THRESHOLD),
    "profit_100k": lambda: (int(runstate.max_profit_ever), PROFIT_100K_THRESHOLD),
    "diversified_trader": lambda: (len(HOME_SYSTEM_GOODS & runstate.goods_sold_ever), len(HOME_SYSTEM_GOODS)),
    "background_galaxy_maxed": lambda: (background_world_count(), ENDGAME_BACKGROUND_WORLD_CAP),
    "charter_veteran": lambda: (min(runstate.charters_completed, CHARTER_VETERAN_COUNT), CHARTER_VETERAN_COUNT),
    "full_roster": lambda: (len(runstate.captains_met), len(CAPTAINS)),
    "storm_watcher": lambda: (min(records["weather_events"], WEATHER_ACHIEVEMENT_EVENTS), WEATHER_ACHIEVEMENT_EVENTS),
    "curio_cabinet": lambda: (len(records["curios"]), len(CURIO_IDS)),
    "market_maker": lambda: (min(records["exchange_fills"], EXCHANGE_MARKET_MAKER_FILLS), EXCHANGE_MARKET_MAKER_FILLS),
    "board_member": lambda: (min(records["cartel_moves"], CARTEL_ACHIEVEMENT_MOVES), CARTEL_ACHIEVEMENT_MOVES),
    "gold_standard": lambda: (sum(1 for c in CRISIS_IDS if records["crisis_best"].get(c, {}).get("medal") == "gold"), len(CRISIS_IDS)),
    "chain_par": lambda: (min(_chain_gold_count(), CHAIN_GOLD_ACHIEVEMENT), CHAIN_GOLD_ACHIEVEMENT),
    "chain_shared": lambda: (_chain_chapter_solved(3), _chain_chapter_size(3)),
    "chain_master": lambda: (len(records["chain_best"]), len(CHAIN_PUZZLES)),
}


def _chain_gold_count():
    return sum(1 for pid, e in records["chain_best"].items() if chain_medal_for(CHAIN_BY_ID[pid], e["units"], e["ships"]) == "gold")


def _chain_chapter_solved(chapter):
    return sum(1 for p in CHAIN_PUZZLES if p["chapter"] == chapter and p["id"] in records["chain_best"])


def _chain_chapter_size(chapter):
    return sum(1 for p in CHAIN_PUZZLES if p["chapter"] == chapter)


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
    if runstate.sandbox_active:  # Z-18: nothing in the sandbox earns anything; the real list is shown as it was
        return list(runstate._sandbox_real["earned"])
    return [
        entry["id"]
        for entry in ACHIEVEMENTS
        if entry["id"] in runstate.legacy_achievements or ACHIEVEMENT_CHECKS[entry["id"]]()
    ]


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
            }
        )
    return summary


_toast_hide_proxy = None

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    earned = set(achievement_ids_earned())
    _story_reach_all(earned)  # W1: every toast check / load baseline also unlocks story chapters
    return earned


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement, the
    opening one, and the two cluster beats that have no achievement of
    their own (the Rift Colonies and the Umbral Deep), via the shared
    story-chapters.js. Idempotent and silent: no story script, or a chapter
    id it does not know, simply does nothing. Never touches the save."""
    if runstate.sandbox_active:  # Z-18: chapters belong to the real game
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)
    if outer_reaches_unlocked():
        story.reach("rift_colonies")
    if umbral_reach_unlocked():
        story.reach("umbral_deep")


def show_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")

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
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], ACHIEVEMENT_TOAST_DURATION_MS)


# J17 — a one-time callout the first time any ship is automated,
# persisted so it never re-fires after being loaded from a save that
# already has an automated ship on it.


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass)."""
    current = _earned_snapshot()
    newly_earned_ids = current - runstate._previously_earned_ids
    runstate._previously_earned_ids = current
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if not newly_earned:
        return
    _ribbon_flourish()
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


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
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = (
            "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        )
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"\U0001F3C6 {entry['label']}" if entry["earned"] else entry["label"]
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


RIBBON_FLOURISH_MS = 1200


def _ribbon_flourish():
    """A brief glow on the ribbon when something unlocks. Skipped under
    reduced motion or with the Effects toggle off."""
    ribbon = document.getElementById("ledger-ribbon")
    if ribbon is None or not _effects_on():
        return

    def _clear():
        ribbon.classList.remove("ledger-ribbon--flourish")

    ribbon.classList.add("ledger-ribbon--flourish")
    setTimeout(create_proxy(_clear), RIBBON_FLOURISH_MS)
