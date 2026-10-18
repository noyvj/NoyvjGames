"""Achievements: catalog, checks, progress, panel, toast and story-chapter reach."""

import json

from js import document, setTimeout
from pyodide.ffi import create_proxy

import loop_runstate as runstate
from loop_career import career_closed_categories, career_plates, career_speed
from loop_rules import (
    CIRCULARITY_INVESTMENTS, GOODS_CATEGORIES, PLATES, REAL_WORLD_CIRCULARITY_BENCHMARK,
    SECRET_GOODS_CATEGORY, SHOCKED_CLOSE_TARGET,
)


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration. Every achievement's earned status is a pure function of
# state that already exists elsewhere in this module, recomputed fresh
# every call — never a separately hand-maintained "earned" flag.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as the other climate games' reference
    integrations: the boot script fetches achievements.json and hands it
    to Python as a window global before this file runs; the pytest
    harness's fake `js` module has no such attribute, so this falls
    through to reading the file straight off disk, keeping the module
    importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Loop's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

CAPITAL_COMMITTED_TARGET = 300.0
TRADE_SURPLUS_TARGET = 500.0
STREAK_5_TARGET = 5
STREAK_10_TARGET = 10
CLEAN_HANDS_MIN_CYCLES = 10
LIFETIME_MAJORITY_MIN_CYCLES = 5
SCORE_PRAGMATIST_TARGET = 1000.0
SCORE_PRAGMATIST_MIN_FRACTION = 0.5
SCORE_PRAGMATIST_MIN_CYCLES = 10
SCORE_MASTER_TARGET = 2000.0
SCORE_MASTER_MIN_FRACTION = 0.9
SCORE_MASTER_MIN_CYCLES = 15
SERIAL_REDESIGNER_TARGET = 2
GOODS_EXPLORER_TARGET = 2

# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged. The four fraction-tier
# achievements (quarter/half/three_quarter/loop_closed) also double as
# H13's "toast callouts at circular-fraction milestones" — they're keyed
# to exactly those 25/50/75/100% thresholds on circular_fraction_this_cycle(),
# so the existing achievement-unlock toast (below) already delivers that
# callout without a second, redundant toast system. (V-E-5 audit,
# planning/TODO.md: the one real overlap this created — "loop_closed"
# firing in the same action as the H3 loop-closed banner — is sequenced
# in `_run_action()`/`_check_new_achievements_for_toast()` below, not
# fixed by adding a new toast.)
ACHIEVEMENT_CHECKS = {
    "first_fix": lambda: any(runstate.chain.circularity_investment[m] >= 1 for m in CIRCULARITY_INVESTMENTS),
    "full_toolkit": lambda: all(runstate.chain.circularity_investment[m] >= 1 for m in CIRCULARITY_INVESTMENTS),
    "trade_partner": lambda: runstate.chain.trade_link_investment >= 1 or runstate.chain.regional_trade_investment >= 1,
    "dual_sourcing": lambda: runstate.chain.trade_link_investment >= 1 and runstate.chain.regional_trade_investment >= 1,
    "quarter_loop": lambda: runstate.chain.circular_fraction_this_cycle() >= 0.25,
    "half_loop": lambda: runstate.chain.circular_fraction_this_cycle() >= 0.5,
    "three_quarter_loop": lambda: runstate.chain.circular_fraction_this_cycle() >= 0.75,
    "loop_closed": lambda: runstate.chain.is_loop_closed(),
    "lifetime_majority": lambda: (
        runstate.chain.lifetime_circular_fraction() >= 0.5
        and len(runstate.chain.circular_fraction_log) >= LIFETIME_MAJORITY_MIN_CYCLES
    ),
    "beyond_benchmark": lambda: runstate.chain.lifetime_circular_fraction() > REAL_WORLD_CIRCULARITY_BENCHMARK,
    "first_export": lambda: runstate.chain.lifetime_export_revenue > 0.0,
    "trade_surplus_500": lambda: runstate.chain.lifetime_export_revenue >= TRADE_SURPLUS_TARGET,
    "streak_5": lambda: runstate.chain.best_closed_loop_streak >= STREAK_5_TARGET,
    "streak_10": lambda: runstate.chain.best_closed_loop_streak >= STREAK_10_TARGET,
    "clean_hands": lambda: (
        len(runstate.chain.circular_fraction_log) >= CLEAN_HANDS_MIN_CYCLES and runstate.chain.total_extracted == 0.0
    ),
    "capital_committed": lambda: runstate.chain.lifetime_investment_spend >= CAPITAL_COMMITTED_TARGET,
    "score_pragmatist": lambda: (
        runstate.chain.score() >= SCORE_PRAGMATIST_TARGET
        and runstate.chain.lifetime_circular_fraction() >= SCORE_PRAGMATIST_MIN_FRACTION
        and len(runstate.chain.circular_fraction_log) >= SCORE_PRAGMATIST_MIN_CYCLES
    ),
    "score_master": lambda: (
        runstate.chain.score() >= SCORE_MASTER_TARGET
        and runstate.chain.lifetime_circular_fraction() >= SCORE_MASTER_MIN_FRACTION
        and len(runstate.chain.circular_fraction_log) >= SCORE_MASTER_MIN_CYCLES
    ),
    "serial_redesigner": lambda: runstate.chains_completed_count >= SERIAL_REDESIGNER_TARGET,
    "goods_explorer": lambda: len(runstate.goods_categories_tried) >= GOODS_EXPLORER_TARGET,
    # H14: a badge for trying every goods-flavor set.
    "goods_collector": lambda: len(runstate.goods_categories_tried & set(GOODS_CATEGORIES)) >= len(GOODS_CATEGORIES),
    # GH-20: speed-loop achievements, remembered across chains (see career_speed).
    "speed_close": lambda: "cycle12" in career_speed,
    "lean_close": lambda: "lean" in career_speed,
    "no_trade_close": lambda: "no_trade" in career_speed,
    # GH-15 / GH-14: the plate collection and the secret yard.
    "plate_collector": lambda: len(career_plates) >= len(PLATES),
    "yard_boss": lambda: SECRET_GOODS_CATEGORY in career_closed_categories,
    # GH-3: closed cycles that landed on a market shock (the mode is opt-in).
    "shock_absorber": lambda: runstate.chain.shocks_shrugged >= SHOCKED_CLOSE_TARGET,
    # GH-5: pulled ahead of the scripted Rival Corporation (the race is opt-in).
    "rival_overtaken": lambda: runstate.chain.rival_crossover_cycle is not None,
}

# GH-20: shown in the achievements panel only, never as an unlock toast.
SILENT_ACHIEVEMENTS = {"speed_close", "lean_close", "no_trade_close"}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "invest in either trade partner for the first time".
ACHIEVEMENT_PROGRESS = {
    "full_toolkit": lambda: (
        sum(1 for m in CIRCULARITY_INVESTMENTS if runstate.chain.circularity_investment[m] >= 1),
        len(CIRCULARITY_INVESTMENTS),
    ),
    "quarter_loop": lambda: (min(100, round(runstate.chain.circular_fraction_this_cycle() * 100)), 25),
    "half_loop": lambda: (min(100, round(runstate.chain.circular_fraction_this_cycle() * 100)), 50),
    "three_quarter_loop": lambda: (min(100, round(runstate.chain.circular_fraction_this_cycle() * 100)), 75),
    "lifetime_majority": lambda: (min(100, round(runstate.chain.lifetime_circular_fraction() * 100)), 50),
    "trade_surplus_500": lambda: (
        min(round(runstate.chain.lifetime_export_revenue), int(TRADE_SURPLUS_TARGET)),
        int(TRADE_SURPLUS_TARGET),
    ),
    "streak_5": lambda: (min(runstate.chain.best_closed_loop_streak, STREAK_5_TARGET), STREAK_5_TARGET),
    "streak_10": lambda: (min(runstate.chain.best_closed_loop_streak, STREAK_10_TARGET), STREAK_10_TARGET),
    "capital_committed": lambda: (
        min(round(runstate.chain.lifetime_investment_spend), int(CAPITAL_COMMITTED_TARGET)),
        int(CAPITAL_COMMITTED_TARGET),
    ),
    "score_pragmatist": lambda: (
        min(round(runstate.chain.score()), int(SCORE_PRAGMATIST_TARGET)),
        int(SCORE_PRAGMATIST_TARGET),
    ),
    "score_master": lambda: (
        min(round(runstate.chain.score()), int(SCORE_MASTER_TARGET)),
        int(SCORE_MASTER_TARGET),
    ),
    "serial_redesigner": lambda: (min(runstate.chains_completed_count, SERIAL_REDESIGNER_TARGET), SERIAL_REDESIGNER_TARGET),
    "goods_explorer": lambda: (min(len(runstate.goods_categories_tried), GOODS_EXPLORER_TARGET), GOODS_EXPLORER_TARGET),
    "goods_collector": lambda: (len(runstate.goods_categories_tried & set(GOODS_CATEGORIES)), len(GOODS_CATEGORIES)),
    "plate_collector": lambda: (len(career_plates), len(PLATES)),
    "shock_absorber": lambda: (min(runstate.chain.shocks_shrugged, SHOCKED_CLOSE_TARGET), SHOCKED_CLOSE_TARGET),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
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
            }
        )
    return summary


# H-31: achievements earned since the panel was last opened (they make the button glow), and those whose
# unlock flourish has already played (so a re-render of the open panel does not replay it).
_unseen_achievements = set()
_flourished_achievements = set()


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    fresh = set(_unseen_achievements) if runstate.achievements_open else set()
    if runstate.achievements_open:
        _unseen_achievements.clear()
    new_note = f" · {len(_unseen_achievements)} new" if _unseen_achievements and not runstate.achievements_open else ""
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)}){new_note}"
    )
    # H-31: a progress ring on the button (ten steps) and a glow while something new waits unseen.
    for step in range(11):
        toggle.classList.remove(f"achievements-toggle--p{step}")
    toggle.classList.add("achievements-toggle")
    toggle.classList.add(f"achievements-toggle--p{round(10 * earned_count / max(1, len(ACHIEVEMENTS)))}")
    if _unseen_achievements and not runstate.achievements_open:
        toggle.classList.add("achievements-toggle--new")
    else:
        toggle.classList.remove("achievements-toggle--new")
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        if entry["earned"] and entry["id"] in fresh and entry["id"] not in _flourished_achievements:
            card.className += " achievement-card--new"  # H-31: the one-time unlock flourish (still under reduced motion)
            _flourished_achievements.add(entry["id"])
        card.dataset.achievementId = entry["id"]

        if entry["earned"]:
            # H-31: an earned badge sits inside a small closed-loop ring.
            ring = document.createElement("span")
            ring.className = "achievement-ring"
            ring.setAttribute("aria-hidden", "true")
            ring.innerText = "\u21bb"
            card.appendChild(ring)

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

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub Pages
    # subpath fix). Rebuilt each open alongside the cards since the panel
    # is cleared first. The hub-side script.js registration that makes
    # Loop's save data actually show up on that dashboard is a root-file
    # change, out of scope for this games/loop/-only dispatch.
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


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())
    _story_reach_all(runstate._achievements_seen_ids)  # W1: a loaded save's earned chapters come back too


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing.
    Story progress lives in the browser's localStorage, never in the save."""
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


def _display_achievement_toast(message):
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


def _check_new_achievements_for_toast(delay_ms=0):
    """Called after every player action that could change earned status
    — never from render() itself, since load_state() also calls render()
    and a loaded save with several achievements already earned must not
    flood the player with toasts for all of them at once.

    H13 audit fix (planning/TODO.md V-E-5): "loop_closed" is itself one of
    the checkable achievements, so the exact action that closes the loop
    for the first time earns it in the very same tick that
    `_show_loop_closed_banner()` (below) also fires — two one-shot
    notifications from one event. `_run_action()` passes a non-zero
    `delay_ms` (the loop-closed banner's own visible duration) on exactly
    that transition, so the toast waits its turn instead of stacking with
    the banner. Every other call site passes 0 (show immediately), the
    original behavior. Which achievement(s) newly unlocked — and whether
    they get shown at all — is decided the same way regardless of timing;
    only *when* the resulting toast becomes visible changes."""
    earned_now = set(achievement_ids_earned())
    _story_reach_all(earned_now)
    newly = earned_now - runstate._achievements_seen_ids
    runstate._achievements_seen_ids = earned_now
    if not newly:
        return
    _unseen_achievements.update(newly)  # H-31: the button glows until the panel is opened
    update_achievements_display()

    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    labels = [by_id[aid]["label"] for aid in sorted(newly) if aid in by_id and aid not in SILENT_ACHIEVEMENTS]
    if not labels:
        return

    if len(labels) == 1:
        message = f"🏆 Achievement unlocked: {labels[0]}"
    else:
        message = f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels)

    if delay_ms <= 0:
        _display_achievement_toast(message)
        return

    def _show(*args):
        _display_achievement_toast(message)
        proxy.destroy()

    proxy = create_proxy(_show)
    setTimeout(proxy, delay_ms)
