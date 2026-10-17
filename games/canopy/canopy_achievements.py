"""Achievements (catalog, checks, progress, toast, grove wall)."""

import json

from js import document, setTimeout
from pyodide.ffi import create_proxy

import canopy_runstate as runstate
from canopy_forestlog import WILDLIFE_SPECIES
from canopy_helpers import _announce
from canopy_rules import ACCRUING_STATES, BARE, PRESERVED, RECOVERED, REPLANTING, expedition_meta
from canopy_valuation import (
    BADGE_HARVESTER, _max_clear_count, _peak_now, _total_clear_count, playstyle_badge,
    standing_forest_value, state_breakdown, total_biodiversity,
)
from canopy_worldvars import (
    CHALLENGE_NO_HIGHLAND, CHALLENGE_PACIFIST, CHALLENGE_SCORCHED, CHALLENGE_SPRINT,
    TIER_ACHIEVEMENT_THRESHOLDS, _gb_toast_queue,
)


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the
# reference integration for the hub-wide achievements framework; this is
# Canopy's own catalog, grounded in its actual mechanics (plot management,
# soil degradation, biodiversity, stakeholder relations, income vs.
# standing-value playstyle) rather than generic filler.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that
# already exists elsewhere in this module, recomputed fresh on every call
# — never a separately hand-maintained "earned" flag ("derive, don't
# track", same discipline SOL's own achievements follow). Five checks
# genuinely needed new tracked state (see the module-level declarations
# above, `total_replants` through `community_relations_min_ever`) because
# the thing they measure ("this ever happened") isn't recoverable from
# state that only reflects the *current* moment — e.g. a plot's
# biodiversity resets to 0 the instant it's cleared, so "has any plot ever
# shown wildlife" has no live signal to read without `plots_with_wildlife_
# ever`. Every other check below reads plots/total_income/community_
# relations directly.
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract SOL's game.py established (itself following
    Le Champ de Mots' `_read_json_asset()`): the page's boot script
    fetches achievements.json and hands it to Python as a window global
    before this file runs; the pytest harness's fake `js` module simply
    has no such attribute, so this falls through to reading the file
    straight off disk, which keeps the module importable outside a real
    browser."""
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
# are additive, not core to Canopy's own gameplay, so this degrades to "no
# achievements catalog" instead.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

THRIVING_FOREST_BIODIVERSITY_THRESHOLD = 25.0
STANDING_FORTUNE_THRESHOLD = 1000.0
QUICK_MONEY_THRESHOLD = 1000.0
BALANCED_LEDGER_THRESHOLD = 500.0
TRUE_CONSERVATIONIST_STANDING_THRESHOLD = 300.0
RESOURCEFUL_EXTRACTOR_CLEAR_COUNT = 15
SOIL_SCARRED_CLEAR_COUNT = 5
OLD_GROWTH_GROVE_MATURE_COUNT = 5
BIODIVERSITY_HAVEN_WILDLIFE_COUNT = 10
REBUILT_TRUST_LOW_WATERMARK = 10
REBUILT_TRUST_HIGH_WATERMARK = 50
GENEROUS_HOST_GRANT_COUNT = 10
PRINCIPLED_REFUSAL_DECLINE_COUNT = 10
FLOURISHING_CANOPY_STANDING_THRESHOLD = 500.0


def _mature_plot_count():
    """How many standing (PRESERVED/RECOVERED) plots have reached full
    maturity_fraction() -- i.e. ticks_intact has caught up to
    MATURITY_TICKS, the same threshold the color-gradient rendering caps
    out at."""
    return sum(
        1
        for plot in runstate.plots
        if plot.state in ACCRUING_STATES and plot.maturity_fraction() >= 1.0
    )


def _wildlife_active_count():
    return sum(1 for plot in runstate.plots if plot.has_wildlife())


def _all_four_states_present():
    counts = state_breakdown()
    return all(counts[state] >= 1 for state in (PRESERVED, BARE, REPLANTING, RECOVERED))


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_clear": lambda: _total_clear_count() >= 1,
    "first_replant": lambda: runstate.total_replants >= 1,
    "first_recovery": lambda: runstate.total_recoveries >= 1,
    "standing_tall": lambda: _mature_plot_count() >= 1,
    "old_growth_grove": lambda: _mature_plot_count() >= OLD_GROWTH_GROVE_MATURE_COUNT,
    "wildlife_returns": lambda: len(runstate.plots_with_wildlife_ever) >= 1,
    "biodiversity_haven": lambda: _wildlife_active_count() >= BIODIVERSITY_HAVEN_WILDLIFE_COUNT,
    "thriving_forest": lambda: total_biodiversity() >= THRIVING_FOREST_BIODIVERSITY_THRESHOLD,
    "standing_fortune": lambda: standing_forest_value() >= STANDING_FORTUNE_THRESHOLD,
    "quick_money": lambda: runstate.total_income >= QUICK_MONEY_THRESHOLD,
    "balanced_ledger": lambda: (
        runstate.total_income >= BALANCED_LEDGER_THRESHOLD
        and standing_forest_value() >= BALANCED_LEDGER_THRESHOLD
    ),
    "true_conservationist": lambda: (
        _total_clear_count() == 0
        and standing_forest_value() >= TRUE_CONSERVATIONIST_STANDING_THRESHOLD
    ),
    "resourceful_extractor": lambda: _total_clear_count() >= RESOURCEFUL_EXTRACTOR_CLEAR_COUNT,
    "soil_scarred": lambda: _max_clear_count() >= SOIL_SCARRED_CLEAR_COUNT,
    "community_ally": lambda: runstate.community_relations >= 100,
    "rebuilt_trust": lambda: (
        runstate.community_relations_min_ever <= REBUILT_TRUST_LOW_WATERMARK
        and runstate.community_relations >= REBUILT_TRUST_HIGH_WATERMARK
    ),
    "generous_host": lambda: runstate.stakeholder_grants_count >= GENEROUS_HOST_GRANT_COUNT,
    "principled_refusal": lambda: runstate.stakeholder_declines_count >= PRINCIPLED_REFUSAL_DECLINE_COUNT,
    "flourishing_canopy": lambda: (
        state_breakdown()[BARE] == 0
        and state_breakdown()[REPLANTING] == 0
        and standing_forest_value() >= FLOURISHING_CANOPY_STANDING_THRESHOLD
    ),
    "every_stage_at_once": lambda: _all_four_states_present(),
    # B3: Highland Grove's own unlock IS the achievement condition -- no
    # extra threshold needed, `highland_unlocked` already is the pure,
    # already-derived boolean this pattern wants.
    "second_growth": lambda: runstate.highland_unlocked,
    # GB-22: the standing-value tiers above 1,000 (which standing_fortune
    # already covers). Read off the best value reached, so a later clear
    # cannot un-earn a tier the forest already grew into.
    "tier_grove": lambda: _peak_now() >= TIER_ACHIEVEMENT_THRESHOLDS["tier_grove"],
    "tier_woodland": lambda: _peak_now() >= TIER_ACHIEVEMENT_THRESHOLDS["tier_woodland"],
    "tier_old_growth_steward": lambda: _peak_now() >= TIER_ACHIEVEMENT_THRESHOLDS["tier_old_growth_steward"],
    # GB-17: one badge per challenge, earned by finishing that challenge in this session.
    "challenge_pacifist": lambda: runstate.current_challenge == CHALLENGE_PACIFIST and runstate.challenge_complete_tick is not None,
    "challenge_scorched": lambda: runstate.current_challenge == CHALLENGE_SCORCHED and runstate.challenge_complete_tick is not None,
    "challenge_sprint": lambda: runstate.current_challenge == CHALLENGE_SPRINT and runstate.challenge_complete_tick is not None,
    "challenge_no_highland": lambda: runstate.current_challenge == CHALLENGE_NO_HIGHLAND and runstate.challenge_complete_tick is not None,
    # GB-21: the clear-cut and the Harvester playstyle badge it feeds.
    "quick_payout": lambda: runstate.clear_cuts_total >= 1,
    "harvester_badge": lambda: runstate.clear_cuts_total >= 1 and playstyle_badge() == BADGE_HARVESTER,
    # GB-3: finish an Expedition (12 seasons), and finish them on two different seeds. Read from the per-browser records.
    "expedition_complete": lambda: expedition_finished_count() >= 1,
    "two_maps": lambda: len(expedition_meta["best"]) >= 2,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for the rest (one-shot
# milestones like "clear your first plot" don't get a fake "0 of 1").
ACHIEVEMENT_PROGRESS = {
    "old_growth_grove": lambda: (_mature_plot_count(), OLD_GROWTH_GROVE_MATURE_COUNT),
    "biodiversity_haven": lambda: (_wildlife_active_count(), BIODIVERSITY_HAVEN_WILDLIFE_COUNT),
    "thriving_forest": lambda: (
        round(min(total_biodiversity(), THRIVING_FOREST_BIODIVERSITY_THRESHOLD), 1),
        THRIVING_FOREST_BIODIVERSITY_THRESHOLD,
    ),
    "standing_fortune": lambda: (int(standing_forest_value()), int(STANDING_FORTUNE_THRESHOLD)),
    "quick_money": lambda: (int(runstate.total_income), int(QUICK_MONEY_THRESHOLD)),
    "resourceful_extractor": lambda: (_total_clear_count(), RESOURCEFUL_EXTRACTOR_CLEAR_COUNT),
    "soil_scarred": lambda: (_max_clear_count(), SOIL_SCARRED_CLEAR_COUNT),
    "generous_host": lambda: (runstate.stakeholder_grants_count, GENEROUS_HOST_GRANT_COUNT),
    "principled_refusal": lambda: (runstate.stakeholder_declines_count, PRINCIPLED_REFUSAL_DECLINE_COUNT),
    "tier_grove": lambda: (int(min(_peak_now(), 2500.0)), 2500),
    "tier_woodland": lambda: (int(min(_peak_now(), 5000.0)), 5000),
    "tier_old_growth_steward": lambda: (int(min(_peak_now(), 10000.0)), 10000),
}


# GN-1 (user report 2026-10-10): achievements used to be recomputed from the live session only, so starting a new
# level (a fresh session) made every one of them vanish. This ledger keeps every id the player has ever had satisfied;
# it survives reset_session(), is written out through "achievements_earned" and seeded back from a loaded save.
achievement_ledger = set()


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
    now = {entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()}
    achievement_ledger.update(now)  # GN-1: once earned, earned for the whole game
    return [entry["id"] for entry in ACHIEVEMENTS if entry["id"] in achievement_ledger]


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
    return set(achievement_ids_earned())


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


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing."""
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


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass, e.g. several achievements clearing at once on
    a big tick)."""
    current = _earned_snapshot()
    _story_reach_all(current)
    newly_earned_ids = current - runstate._previously_earned_ids
    runstate._previously_earned_ids = current
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    messages = []
    if len(newly_earned) == 1:
        messages.append(f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}")
    elif newly_earned:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        messages.append(f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}")
    for message in messages:
        _announce(message)  # B-7: achievements are not in the forest log; GB toasts already are
    messages.extend(_gb_toast_queue)  # GB batch 1: discoveries, tiers, seasons
    del _gb_toast_queue[:]
    if messages:
        show_achievement_toast("  \u00b7  ".join(messages))


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def grove_wall_glyph(position):
    """B-31: the grove wall reuses the wildlife icons already in the game, cycling in catalog order."""
    return WILDLIFE_SPECIES[position % len(WILDLIFE_SPECIES)][0]


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
    panel.className = "section achievements-panel grove-wall"  # B-31: laid out like the plot grid
    for position, entry in enumerate(achievements_summary()):
        card = document.createElement("div")
        card.className = (
            "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        )
        card.dataset.achievementId = entry["id"]

        glyph = document.createElement("span")  # B-31: wildlife icon, a dim silhouette until earned
        glyph.className = "achievement-card-glyph" if entry["earned"] else "achievement-card-glyph achievement-card-glyph--locked"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = grove_wall_glyph(position)
        card.appendChild(glyph)

        status = document.createElement("p")
        status.className = "achievement-card-status"
        status.innerText = "Earned" if entry["earned"] else "Locked"
        card.appendChild(status)

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

    # A link out to the hub-wide achievements dashboard (planning/
    # ACHIEVEMENTS-SYSTEM-DESIGN.md §5, and the "roll achievements out
    # everywhere" TODO's toast+hub-link requirement). Canopy's own
    # achievements.json/panel/get_state() wiring is entirely self-contained
    # here, but registering this game in the *hub's* script.js
    # (GAMES_WITH_ACHIEVEMENTS) is a root-level file outside games/canopy/
    # -- deliberately left as a follow-up so this game's rollout doesn't
    # need to touch shared hub files while other games are being worked on
    # in parallel. The link still works today (it just takes a signed-in
    # visitor to the hub, where Canopy won't appear in the dashboard list
    # until that follow-up lands) and needs no change on this end once it
    # does.
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


def expedition_finished_count():
    return int(expedition_meta["finished"])
