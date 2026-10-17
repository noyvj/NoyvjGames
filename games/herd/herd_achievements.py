"""Achievements: the checks, the progress readouts, the panel, the unlock toast and the one-time milestone callouts.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import json
import os

from js import document, setTimeout
from pyodide.ffi import create_proxy

import herd_runstate as runstate
from herd_rules import (
    CERTIFICATION_ROUNDS_REQUIRED, CLEAN_OPERATOR_MAX_PRESSURE, CLEAN_OPERATOR_MIN_ROUND, DECOUPLING_MEASURES,
    MAX_PLANT_BASED_FRACTION, REAL_WORLD_REDUCTION_FRACTION,
)
from herd_model import rules_unranked


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration. Every achievement's earned status is a pure function of
# state that already exists elsewhere in this module, recomputed fresh
# every call — never a separately hand-maintained "earned" flag. Two
# checks needed genuinely new tracked state (max_pressure_fraction_seen
# on FarmState, mutated only in advance_round() where pressure is
# actually computed) — nothing else in this module records the worst
# pressure a session has seen.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()` / Le
    Champ de Mots' `_read_json_asset()`: the boot script fetches
    achievements.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off
    disk, keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Herd's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

GROWING_OPERATION_TARGET = 10
MAJOR_OPERATION_TARGET = 25
LONG_HAUL_TARGET = 25
CENTURY_FARM_TARGET = 50
# Starting funds is exactly 300 (STARTING_FUNDS), so a target of 300
# would be trivially "earned" on a brand-new, untouched farm -- picked
# 400 specifically so it requires genuine progress.
SCORE_400_TARGET = 400
DECOUPLING_DIVIDEND_TARGET = 50.0
OUTPERFORMING_BASELINE_MIN_ROUND = 5


def _all_three_measures_invested():
    return all(runstate.farm.decoupling_investment[m] >= 1 for m in DECOUPLING_MEASURES)


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_herd": lambda: runstate.farm.herd_size >= 1,
    "growing_operation": lambda: runstate.farm.herd_size >= GROWING_OPERATION_TARGET,
    "major_operation": lambda: runstate.farm.herd_size >= MAJOR_OPERATION_TARGET,
    "first_decoupling": lambda: any(runstate.farm.decoupling_investment[m] >= 1 for m in DECOUPLING_MEASURES),
    "all_three_measures": _all_three_measures_invested,
    "quarter_decoupled": lambda: runstate.farm.decoupled_fraction() >= 0.25,
    "half_decoupled": lambda: runstate.farm.decoupled_fraction() >= 0.5,
    "fully_decoupled": lambda: runstate.farm.decoupled_fraction() >= 0.9,
    "sustainably_certified": lambda: runstate.farm.certified,
    "plant_pioneer": lambda: runstate.farm.plant_pivot_investment >= 1,
    "half_plant_based": lambda: runstate.farm.plant_based_fraction() >= 0.3,
    "max_plant_pivot": lambda: runstate.farm.plant_based_fraction() >= MAX_PLANT_BASED_FRACTION,
    "real_world_match": lambda: runstate.farm.decoupled_fraction() >= REAL_WORLD_REDUCTION_FRACTION,
    "outperforming_baseline": lambda: (
        runstate.farm.round_number > OUTPERFORMING_BASELINE_MIN_ROUND and runstate.farm.score() > runstate.farm.counterfactual_score()
    ),
    "decoupling_dividend": lambda: (
        runstate.farm.score() - runstate.farm.counterfactual_score() >= DECOUPLING_DIVIDEND_TARGET
    ),
    "clean_operator": lambda: (
        runstate.farm.round_number >= CLEAN_OPERATOR_MIN_ROUND
        and runstate.farm.max_pressure_fraction_seen < CLEAN_OPERATOR_MAX_PRESSURE
    ),
    "long_haul": lambda: runstate.farm.round_number >= LONG_HAUL_TARGET,
    "century_farm": lambda: runstate.farm.round_number >= CENTURY_FARM_TARGET,
    # F-1: a bigger opening purse would make this one free, so a custom-rules run cannot earn it.
    "score_400": lambda: runstate.farm.score() >= SCORE_400_TARGET and not rules_unranked(),
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "invest in all three measures at least once."
ACHIEVEMENT_PROGRESS = {
    "growing_operation": lambda: (min(runstate.farm.herd_size, GROWING_OPERATION_TARGET), GROWING_OPERATION_TARGET),
    "major_operation": lambda: (min(runstate.farm.herd_size, MAJOR_OPERATION_TARGET), MAJOR_OPERATION_TARGET),
    "quarter_decoupled": lambda: (min(100, round(runstate.farm.decoupled_fraction() * 100)), 25),
    "half_decoupled": lambda: (min(100, round(runstate.farm.decoupled_fraction() * 100)), 50),
    "fully_decoupled": lambda: (min(100, round(runstate.farm.decoupled_fraction() * 100)), 90),
    "half_plant_based": lambda: (min(100, round(runstate.farm.plant_based_fraction() * 100)), 30),
    "max_plant_pivot": lambda: (
        min(100, round(runstate.farm.plant_based_fraction() * 100)),
        round(MAX_PLANT_BASED_FRACTION * 100),
    ),
    "real_world_match": lambda: (
        min(100, round(runstate.farm.decoupled_fraction() * 100)),
        round(REAL_WORLD_REDUCTION_FRACTION * 100),
    ),
    "decoupling_dividend": lambda: (
        max(0, min(round(DECOUPLING_DIVIDEND_TARGET), round(runstate.farm.score() - runstate.farm.counterfactual_score()))),
        round(DECOUPLING_DIVIDEND_TARGET),
    ),
    "long_haul": lambda: (min(runstate.farm.round_number, LONG_HAUL_TARGET), LONG_HAUL_TARGET),
    "century_farm": lambda: (min(runstate.farm.round_number, CENTURY_FARM_TARGET), CENTURY_FARM_TARGET),
    "score_400": lambda: (max(0, min(round(runstate.farm.score()), SCORE_400_TARGET)), SCORE_400_TARGET),
    # F-27: the remaining numeric achievements, so every card that is not earned shows how far along it is.
    "first_herd": lambda: (min(runstate.farm.herd_size, 1), 1),
    "first_decoupling": lambda: (min(sum(runstate.farm.decoupling_investment.values()), 1), 1),
    "all_three_measures": lambda: (sum(1 for m in DECOUPLING_MEASURES if runstate.farm.decoupling_investment[m] >= 1), len(DECOUPLING_MEASURES)),
    "sustainably_certified": lambda: (
        min(runstate.farm.certification_streak, CERTIFICATION_ROUNDS_REQUIRED), CERTIFICATION_ROUNDS_REQUIRED
    ),
    "plant_pioneer": lambda: (min(runstate.farm.plant_pivot_investment, 1), 1),
    "outperforming_baseline": lambda: (
        max(0, min(runstate.farm.round_number - 1, OUTPERFORMING_BASELINE_MIN_ROUND)), OUTPERFORMING_BASELINE_MIN_ROUND
    ),
    # Clean Operator is lost for this farm once pressure has gone past the limit: no progress line then.
    "clean_operator": lambda: (
        (min(runstate.farm.round_number, CLEAN_OPERATOR_MIN_ROUND), CLEAN_OPERATOR_MIN_ROUND)
        if runstate.farm.max_pressure_fraction_seen < CLEAN_OPERATOR_MAX_PRESSURE else None
    ),
}

# What one step of each progress readout counts, for the "N to go" line on a card.
ACHIEVEMENT_PROGRESS_UNITS = {
    "growing_operation": " herd units", "major_operation": " herd units", "first_herd": " herd unit",
    "quarter_decoupled": "%", "half_decoupled": "%", "fully_decoupled": "%", "half_plant_based": "%",
    "max_plant_pivot": "%", "real_world_match": "%", "decoupling_dividend": " points", "score_400": " points",
    "long_haul": " rounds", "century_farm": " rounds", "clean_operator": " rounds", "outperforming_baseline": " rounds",
    "sustainably_certified": " rounds", "all_three_measures": " measures", "first_decoupling": " investment",
    "plant_pioneer": " investment",
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    if runstate.sandbox_active:  # GF-24: nothing in the sandbox earns anything; the real farm's list is shown as it was
        return list(runstate._sandbox_real["earned"])
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
                "progress": progress_fn() if progress_fn and not runstate.sandbox_active else None,
                "unit": ACHIEVEMENT_PROGRESS_UNITS.get(entry["id"], ""),
            }
        )
    return summary


def progress_percent(current, target):
    return 0.0 if target <= 0 else max(0.0, min(100.0, current / target * 100.0))


def progress_left_text(current, target, unit=""):
    """"N to go" with the unit the achievement counts in (the exact amount left, never rounded up)."""
    left = max(0, target - current)
    return f"{left}{unit} to go ({current} of {target})"


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    update_achievements_display()


# F-31 -- a livestock or pasture glyph for every achievement card, a barnyard border on earned cards, and a
# short flourish the first time a card is drawn after its achievement was earned (once per card).
ACHIEVEMENT_GLYPHS = {
    "first_herd": "\U0001F404", "growing_operation": "\U0001F402", "major_operation": "\U0001F69C",
    "first_decoupling": "\U0001F33E", "all_three_measures": "\U0001F340", "quarter_decoupled": "\U0001F331",
    "half_decoupled": "\U0001F33F", "fully_decoupled": "\U0001F333", "sustainably_certified": "\U0001F3E1",
    "plant_pioneer": "\U0001F955", "half_plant_based": "\U0001F96C", "max_plant_pivot": "\U0001F33B",
    "real_world_match": "\U0001F41D", "outperforming_baseline": "\U0001F95B", "decoupling_dividend": "\U0001F9C0",
    "clean_operator": "\U0001F9FA", "long_haul": "\U0001F413", "century_farm": "\U0001F411", "score_400": "\U0001F410",
}
ACHIEVEMENT_GLYPH_DEFAULT = "\U0001F404"
achievement_flourish_ids = set()  # earned since the panel last drew them; session only


def achievement_glyph(achievement_id):
    return ACHIEVEMENT_GLYPHS.get(achievement_id, ACHIEVEMENT_GLYPH_DEFAULT)


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
        if entry["earned"] and entry["id"] in achievement_flourish_ids:
            card.className += " achievement-card--new"
            achievement_flourish_ids.discard(entry["id"])
        card.dataset.achievementId = entry["id"]

        glyph = document.createElement("span")
        glyph.className = "achievement-card-glyph"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = achievement_glyph(entry["id"])
        card.appendChild(glyph)

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
            # F-27: a mini bar and the exact amount left, shown on hover or keyboard focus (the
            # card takes focus, so a tap on a phone works too). The text is always in the page.
            card.setAttribute("tabindex", "0")
            card.setAttribute("aria-label", f"{entry['label']}: {progress_left_text(current, target, entry['unit'])}")
            bar = document.createElement("div")
            bar.className = "achievement-card-bar"
            bar.setAttribute("role", "presentation")
            fill = document.createElement("div")
            fill.className = "achievement-card-bar-fill"
            fill.style.width = f"{progress_percent(current, target):.0f}%"
            bar.appendChild(fill)
            card.appendChild(bar)
            left = document.createElement("p")
            left.className = "achievement-card-left"
            left.innerText = progress_left_text(current, target, entry["unit"])
            card.appendChild(left)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub
    # Pages subpath fix). Rebuilt each open alongside the cards since the
    # panel is cleared first. The hub-side script.js registration that
    # makes Herd's save data actually show up on that dashboard is a
    # root-file change, out of scope for this games/herd/-only dispatch.
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


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (grow/invest/advance round) — never from render() itself, since
    load_state() also calls render() and a loaded save with several
    achievements already earned must not flood the player with toasts
    for all of them at once (see _seed_achievement_toast_baseline)."""
    earned_now = set(achievement_ids_earned())
    _story_reach_all(earned_now)
    newly = earned_now - runstate._achievements_seen_ids
    achievement_flourish_ids.update(newly)
    if newly and runstate.achievements_open:
        update_achievements_display()  # draw the new cards now, so the flourish plays when they are earned
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    runstate._achievements_seen_ids = earned_now


# F5/F11/F17 — a second, distinct toast for one-time gameplay nudges
# (not achievements): the half-decoupled callout, the pressure-spike
# callout, and the methane-penalty nudge. Kept separate from the
# achievement toast (same shape Grid keeps its achievement-toast and
# disruption-toast separate) so a nudge is never visually confused with
# an unlock.
_MILESTONE_CALLOUT_MESSAGES = {
    "half_decoupled": (
        "You've cut your emissions-per-herd-unit ratio 50% below baseline. That's what "
        '"decoupled" means: the same herd now emits half as much methane, so growth and '
        "emissions are no longer locked together."
    ),
    "pressure": (
        "Market/regulatory pressure just crossed 25% income loss — sustained methane is now "
        "visibly eating into your income."
    ),
    "methane_penalty": (
        "Your accumulated methane is now cutting a real chunk out of your score — decoupling "
        "measures reduce this without requiring you to shrink your herd."
    ),
}


def _display_milestone_toast(message):
    toast = document.getElementById("milestone-toast")
    text = document.getElementById("milestone-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 5000)


def _check_milestone_callout(prefix=""):
    """Consumes FarmState.just_hit_callout (set at most once per
    advance_round() call) and shows its toast. Called from
    on_advance_round(), not render(), so a save/load round-trip (which
    also calls render()) never replays an old callout."""
    if runstate.farm.just_hit_callout is not None:
        message = _MILESTONE_CALLOUT_MESSAGES.get(runstate.farm.just_hit_callout)
        runstate.farm.just_hit_callout = None
        if message:
            _display_milestone_toast(f"{prefix} {message}".strip())  # GF-3: an audit result is not lost under a callout


# F19 — lightweight pulse feedback on a successful investment click.
# Adds a CSS animation class to the element for a fixed short duration,
# then removes it, same setTimeout+create_proxy technique as the toasts
# above.
def _pulse(element_id):
    element = document.getElementById(element_id)
    element.classList.add("invest-pulse")

    def _unpulse(*args):
        element.classList.remove("invest-pulse")
        proxy.destroy()

    proxy = create_proxy(_unpulse)
    setTimeout(proxy, 350)
