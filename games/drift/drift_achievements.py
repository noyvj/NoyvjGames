"""Achievements: the catalog loaded from achievements.json, the checks and progress, the screen-reader announcer, the toast, the glyphs and the achievements panel."""

import json
import re

from js import document, setTimeout
from pyodide.ffi import create_proxy

import drift_runstate as runstate
from drift_model_region import region
from drift_rules import (
    AHEAD_OF_SCHEDULE_MAX_ROUND, BACKLOG_CLEARED_MIN_ARRIVALS, BALANCED_REGION_MIN_SCORE,
    BUILT_TO_SCALE_TARGET, CAPACITY_TYPES, CENTURY_ARRIVALS_TARGET, CENTURY_INTEGRATED_TARGET,
    CRISIS_AVERTED_MIN_ROUND, INVEST_COST, MODEL_REGION_WELLBEING_SCORE, SERVICES_BACKBONE_TARGET,
    STEADY_GROUND_STREAK_TARGET, SUSTAINED_TRANSITION_MIN_ROUND, SUSTAINED_TRANSITION_MIN_SCORE,
    THRIVING_WELLBEING_SCORE,
)


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration and Grid/Canopy's rollouts. Every achievement's earned
# status is a pure function of state that already exists elsewhere in
# this module, recomputed fresh every call — never a separately
# hand-maintained "earned" flag. Two achievements (steady_ground,
# long_horizon_reached) needed genuinely new tracked state
# (current_stable_streak/best_stable_streak and coda_ever_viewed,
# declared on RegionState above) — nothing else in this module records
# a stable-strain streak or whether the coda has ever been opened.
# Kept institutional/systems-level throughout, consistent with this
# game's sensitivity note in CLAUDE.md's Tech notes section: labels and
# descriptions are about regional capacity and process counts, not
# individual migrant stories.
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

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Drift's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []


def _services_investment_count():
    """Integration Services is invested in for a fixed cost every time
    (INVEST_COST["services"] never changes), so the number of times it's
    been bought is exactly recoverable from the cumulative funds spent on
    it -- no separate counter needed."""
    return round(region.cumulative_services_investment / INVEST_COST["services"])


def _standing_capacity_type_count():
    return sum(1 for t in CAPACITY_TYPES if region.capacity[t] > 0)


def _ever_reached_critical_strain():
    """Z25: reads the sticky _ever_critical_strain flag rather than
    scanning strain_log -- the log itself is capped at
    DRIFT_LOG_MAX_ENTRIES, so scanning it directly would make this
    achievement un-earnable once the round that crossed critical strain
    rolls off the capped list."""
    return region._ever_critical_strain


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_investment": lambda: sum(region.capacity.values()) > 0,
    "full_capacity_portfolio": lambda: all(region.capacity[t] > 0 for t in CAPACITY_TYPES),
    "services_backbone": lambda: _services_investment_count() >= SERVICES_BACKBONE_TARGET,
    "built_to_scale": lambda: region.total_capacity() >= BUILT_TO_SCALE_TARGET,
    "century_arrivals": lambda: region.total_arrivals >= CENTURY_ARRIVALS_TARGET,
    "crisis_averted": lambda: (
        region.round_number >= CRISIS_AVERTED_MIN_ROUND and not _ever_reached_critical_strain()
    ),
    "full_recovery": lambda: _ever_reached_critical_strain() and region.strain_level() == "stable",
    "turning_point_reached": lambda: region.has_crossed_to_net_positive(),
    "ahead_of_schedule": lambda: (
        region.net_positive_round is not None and region.net_positive_round <= AHEAD_OF_SCHEDULE_MAX_ROUND
    ),
    "century_integrated": lambda: region.integrated_population >= CENTURY_INTEGRATED_TARGET,
    "backlog_cleared": lambda: (
        region.total_arrivals >= BACKLOG_CLEARED_MIN_ARRIVALS and region.pending_population() <= 0.01
    ),
    "balanced_region": lambda: (
        region.service_quality() >= BALANCED_REGION_MIN_SCORE
        and region.economic_health() >= BALANCED_REGION_MIN_SCORE
        and region.social_cohesion() >= BALANCED_REGION_MIN_SCORE
    ),
    "thriving_region": lambda: region.wellbeing_score() >= THRIVING_WELLBEING_SCORE,
    "model_region": lambda: region.wellbeing_score() >= MODEL_REGION_WELLBEING_SCORE,
    "economic_engine": lambda: (
        region.cumulative_services_investment > 0
        and region.cumulative_integration_contribution >= region.cumulative_services_investment * 2
    ),
    "steady_ground": lambda: region.best_stable_streak >= STEADY_GROUND_STREAK_TARGET,
    "long_horizon_reached": lambda: region.coda_ever_viewed,
    "sustained_transition": lambda: (
        region.round_number >= SUSTAINED_TRANSITION_MIN_ROUND
        and region.wellbeing_score() >= SUSTAINED_TRANSITION_MIN_SCORE
    ),
}

# Progress readouts, only for achievements with a natural numeric
# scale-up -- a plain earned/not-yet is the honest shape for a one-shot
# or multi-condition milestone (e.g. "reach round 21 with strain never
# critical" doesn't get a fake progress bar, same judgment call Grid's
# ahead_of_the_curve/no_damage_20 make).
ACHIEVEMENT_PROGRESS = {
    "full_capacity_portfolio": lambda: (_standing_capacity_type_count(), len(CAPACITY_TYPES)),
    "services_backbone": lambda: (
        min(_services_investment_count(), SERVICES_BACKBONE_TARGET),
        SERVICES_BACKBONE_TARGET,
    ),
    "built_to_scale": lambda: (
        min(round(region.total_capacity()), round(BUILT_TO_SCALE_TARGET)),
        round(BUILT_TO_SCALE_TARGET),
    ),
    "century_arrivals": lambda: (
        min(round(region.total_arrivals), round(CENTURY_ARRIVALS_TARGET)),
        round(CENTURY_ARRIVALS_TARGET),
    ),
    "century_integrated": lambda: (
        min(round(region.integrated_population), round(CENTURY_INTEGRATED_TARGET)),
        round(CENTURY_INTEGRATED_TARGET),
    ),
    "thriving_region": lambda: (
        min(round(region.wellbeing_score()), round(THRIVING_WELLBEING_SCORE)),
        round(THRIVING_WELLBEING_SCORE),
    ),
    "model_region": lambda: (
        min(round(region.wellbeing_score()), round(MODEL_REGION_WELLBEING_SCORE)),
        round(MODEL_REGION_WELLBEING_SCORE),
    ),
    "steady_ground": lambda: (
        min(region.best_stable_streak, STEADY_GROUND_STREAK_TARGET),
        STEADY_GROUND_STREAK_TARGET,
    ),
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


# ---- B-7 screen-reader announcements ------------------------------------------------------------
# What a sighted player sees change after an action is also said, in plain short sentences, through the shared
# announcer (shared/announcer.js) when the page has it, otherwise through the game's own #sr-announcer region.
# Only player actions and round results announce; render() never does (the shared announcer joins one tick's
# messages, so an invest that also unlocks an achievement is read as one announcement).
def _shared_announce(text):
    """Speak through shared/announcer.js when the page has it (returns True); otherwise the game's own live
    region is used. Never both, so a screen reader does not read a message twice."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    shared = getattr(window, "NoyvjAnnounce", None)
    if shared is None:
        return False
    try:
        shared.say(str(text))
    except Exception:  # noqa: BLE001 -- an announcement must never break the game
        return False
    return True


_EMOJI_RE = re.compile("[\U0001F000-\U0001FFFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


def _plain(text):
    """Drops emoji and symbol pictographs so a screen reader does not read their names aloud."""
    return re.sub(r"\s+", " ", _EMOJI_RE.sub("", str(text))).strip()


def announce(text):
    """Says text for a screen reader (shared announcer first, the game's own polite region otherwise)."""
    text = _plain(text) if text else ""
    if not text:
        return
    if _shared_announce(text):
        return
    region_el = document.getElementById("sr-announcer")
    if region_el is not None:
        region_el.innerText = text


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


# I-31: a small code-drawn glyph on every achievement card, one route or milestone picture per badge in the
# region's own skyline language (36 by 36, currentColour strokes). Earned badges are drawn solid in the
# earned green, locked ones dashed and dim; a badge earned this session draws itself in once when the
# panel next shows it (a short flourish that Reduce Motion and Animation speed Off remove).
GLYPH_GROUND = '<path class="g-ground" d="M3,30 H33" />'
ACHIEVEMENT_GLYPHS = {
    "first_investment": '<rect x="13" y="12" width="10" height="18" /><path d="M16,17 h1 M19,17 h1 M16,22 h1 M19,22 h1" />',
    "full_capacity_portfolio": '<rect x="5" y="20" width="7" height="10" /><rect x="14" y="11" width="8" height="19" /><rect x="24" y="16" width="7" height="14" />',
    "services_backbone": '<rect x="10" y="26" width="16" height="4" /><rect x="10" y="22" width="16" height="4" /><rect x="10" y="18" width="16" height="4" /><rect x="10" y="14" width="16" height="4" /><rect x="10" y="10" width="16" height="4" />',
    "built_to_scale": '<rect x="4" y="24" width="4" height="6" /><rect x="9" y="21" width="4" height="9" /><rect x="14" y="17" width="4" height="13" /><rect x="19" y="13" width="4" height="17" /><rect x="24" y="9" width="4" height="21" /><rect x="29" y="5" width="4" height="25" />',
    "century_arrivals": ''.join(f'<circle cx="{5 + i * 4.3:.1f}" cy="{22 if i % 2 else 17}" r="1.7" />' for i in range(7)),
    "crisis_averted": '<path d="M18,5 L29,10 V19 C29,25 24,28 18,30 C12,28 7,25 7,19 V10 Z" /><path d="M12,18 L16.5,22 L24,13" />',
    "full_recovery": '<path d="M5,12 L12,25 L18,21 L25,11 L31,7" /><path d="M26,6 H31.5 V11.5" />',
    "turning_point_reached": '<path class="g-dash" d="M4,20 H32" /><path d="M5,29 C14,28 18,22 31,8" /><circle cx="20" cy="20" r="2.6" />',
    "ahead_of_schedule": '<path d="M26,30 V7 L33,11 L26,15" /><path class="g-dash" d="M4,26 H22" />',
    "century_integrated": '<circle cx="9" cy="18" r="5" /><circle cx="18" cy="18" r="5" /><circle cx="27" cy="18" r="5" />',
    "backlog_cleared": '<circle cx="8" cy="24" r="2" /><circle cx="15" cy="24" r="2" /><circle cx="22" cy="24" r="2" /><circle cx="29" cy="24" r="2" /><path d="M9,13 L15,19 L28,6" />',
    "balanced_region": '<rect x="5" y="14" width="6" height="16" /><rect x="15" y="14" width="6" height="16" /><rect x="25" y="14" width="6" height="16" /><path class="g-dash" d="M3,10 H33" />',
    "thriving_region": '<circle cx="18" cy="12" r="4.5" /><path d="M18,3 v2 M18,19 v2 M9,12 h2 M25,12 h2 M11.5,5.5 l1.4,1.4 M23.1,17.1 l1.4,1.4 M24.5,5.5 l-1.4,1.4 M12.9,17.1 l-1.4,1.4" /><rect x="8" y="23" width="6" height="7" /><rect x="22" y="21" width="6" height="9" />',
    "model_region": '<polygon points="18.0,4.0 20.6,10.4 27.5,10.9 22.2,15.4 23.9,22.1 18.0,18.4 12.1,22.1 13.8,15.4 8.5,10.9 15.4,10.4" /><rect x="7" y="24" width="6" height="6" /><rect x="15" y="21" width="6" height="9" /><rect x="23" y="24" width="6" height="6" />',
    "economic_engine": '<circle cx="18" cy="17" r="11" /><path d="M18,24 V11 M12,17 L18,11 L24,17" />',
    "steady_ground": '<path d="M4,19 H32" /><path d="M7,15 v8 M12.5,15 v8 M18,15 v8 M23.5,15 v8 M29,15 v8" />',
    "long_horizon_reached": '<path d="M3,20 C9,9 27,9 33,20 C27,29 9,29 3,20 Z" /><circle cx="18" cy="19.5" r="3.4" />',
    "sustained_transition": '<path d="M5,28 L14,22 L22,16 L31,8" /><circle cx="5" cy="28" r="2" /><circle cx="14" cy="22" r="2" /><circle cx="22" cy="16" r="2" /><circle cx="31" cy="8" r="2" />',
}
fresh_glyph_ids = set()  # badges earned this session whose glyph has not been drawn in yet (transient)


def achievement_glyph_svg(achievement_id, earned=False, fresh=False):
    """The card glyph for one achievement ("" for an id with no drawing)."""
    body = ACHIEVEMENT_GLYPHS.get(achievement_id)
    if body is None:
        return ""
    state = "earned" if earned else "locked"
    extra = " achievement-glyph--fresh" if fresh and earned else ""
    return (
        f'<svg viewBox="0 0 36 36" width="36" height="36" class="achievement-glyph achievement-glyph--{state}{extra}" '
        f'focusable="false" aria-hidden="true">{GLYPH_GROUND}{body}</svg>'
    )


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

        glyph = document.createElement("span")
        glyph.className = "achievement-glyph-slot"
        glyph.innerHTML = achievement_glyph_svg(entry["id"], entry["earned"], entry["id"] in fresh_glyph_ids)
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

        panel.appendChild(card)
    fresh_glyph_ids.clear()  # each new badge's flourish plays once

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub
    # Pages subpath fix). Rebuilt each open alongside the cards since the
    # panel is cleared first. Note: the hub-side script.js registration
    # that makes Drift's save data actually show up on that dashboard is
    # a root-file change, out of scope for this games/drift/-only
    # dispatch — see CLAUDE.md.
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
