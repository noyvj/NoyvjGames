"""Achievements (checks, progress, panel, unlock toast) and the in-game 'What's New' changelog panel.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import json

from js import document

import champ_runstate as runstate
from champ_catalog import _read_json_asset
from champ_util import _element
from champ_stats import automated_plot_count, fully_automated_row_count


# render() is defined in champ_renderer, which comes later in the module list; champ_renderer puts it here when it
# loads (see the end of champ_renderer.py). Calls below find it at run time.
render = None


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) -- retrofit of this
# game's own Milestone 23 slice into the cross-game pattern (per
# planning/TODO.md's "roll achievements out everywhere" checklist). SOL is
# the framework's reference integration; this game is the retrofit case
# the design doc itself calls out, since Milestone 23 shipped a game-local
# achievements slice *before* the cross-game framework existed.
# ===========================================================================
#
# Every one of this section's actual unlock conditions is unchanged from
# Milestone 23: two independent tiers, total plots automated and full
# syllabus weeks fully automated. What's reshaped is *where the catalog
# lives* (achievements.json, the cross-game single source of truth for
# label/description -- §2 -- instead of a hardcoded ACHIEVEMENT_ROW_LABELS
# dict) and *what this file exposes* (achievement_ids_earned() as a
# write-only save-state projection, an unlock toast, and a link to the
# hub-wide dashboard). Needs no new tracked state at all, same as before:
# since §3/Milestone 2 already made plot stages monotonic (a stage never
# regresses), "currently Automated" and "ever reached Automated" are the
# same count, so automated_plot_count()/fully_automated_row_count() are
# plain reads of the farm that already exists.

ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    return _read_json_asset(ACHIEVEMENTS_FILENAME, "ACHIEVEMENTS_JSON")


# Defensive, same posture as SUPPLEMENTARY_NOTES above: a missing/broken
# catalog degrades to "no achievements" rather than taking down the whole
# module import -- achievements are a layer on top of the real farm, not
# core gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError):
    ACHIEVEMENTS = []

ACHIEVEMENTS_BY_ID = {entry["id"]: entry for entry in ACHIEVEMENTS}

ACHIEVEMENT_AUTOMATED_THRESHOLDS = [25, 50, 100, 250, 500, 750]
ACHIEVEMENT_ROW_THRESHOLDS = [1, 5, 11, 23]


def automated_achievement_id(threshold):
    return f"automated_{threshold}"


def row_achievement_id(threshold):
    return f"row_{threshold}"


ACHIEVEMENT_CHECKS = {
    **{
        automated_achievement_id(t): (lambda t=t: automated_plot_count() >= t)
        for t in ACHIEVEMENT_AUTOMATED_THRESHOLDS
    },
    **{
        row_achievement_id(t): (lambda t=t: fully_automated_row_count() >= t)
        for t in ACHIEVEMENT_ROW_THRESHOLDS
    },
}

# Every achievement in this game's catalog has a genuine numeric scale-up
# (a plot count or a row count against a fixed threshold), so every id gets
# a progress readout -- unlike SOL's mix of one-shot milestones and
# numeric ones (ACHIEVEMENTS-SYSTEM-DESIGN.md §3).
ACHIEVEMENT_PROGRESS = {
    **{
        automated_achievement_id(t): (lambda t=t: (automated_plot_count(), t))
        for t in ACHIEVEMENT_AUTOMATED_THRESHOLDS
    },
    **{
        row_achievement_id(t): (lambda t=t: (fully_automated_row_count(), t))
        for t in ACHIEVEMENT_ROW_THRESHOLDS
    },
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order -- the
    cross-game "achievements_earned" save field (ACHIEVEMENTS-SYSTEM-
    DESIGN.md §1). Always recomputed, never itself tracked state."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def _tier_progress(thresholds, id_for):
    """Every crossed threshold (earned, most recent first) plus the next
    one still ahead (with a plain "x of y" progress read-out), or None for
    "next" once every threshold is already cleared. Labels now come from
    the achievements.json catalog -- the single source of truth (§2) --
    rather than being hardcoded here."""
    earned_thresholds = [t for t in thresholds if ACHIEVEMENT_CHECKS[id_for(t)]()]
    remaining_thresholds = [t for t in thresholds if not ACHIEVEMENT_CHECKS[id_for(t)]()]
    next_entry = None
    if remaining_thresholds:
        next_id = id_for(remaining_thresholds[0])
        next_entry = {
            "id": next_id,
            "label": ACHIEVEMENTS_BY_ID[next_id]["label"],
            "current": ACHIEVEMENT_PROGRESS[next_id]()[0],
            "target": remaining_thresholds[0],
        }
    return {
        "earned": [
            {"id": id_for(t), "label": ACHIEVEMENTS_BY_ID[id_for(t)]["label"]}
            for t in reversed(earned_thresholds)
        ],
        "next": next_entry,
    }


def achievements_summary():
    """Game-facing tiered view for the in-game panel -- kept as its own
    shape per ACHIEVEMENTS-SYSTEM-DESIGN.md §3's documented judgment call:
    this game's achievements are naturally tiered (unlike SOL's flat
    checklist), so its panel groups each tier into "earned so far (most
    recent first) + next target" rather than being forced into a flat
    card layout. Both tiers now read their labels from the ACHIEVEMENTS
    catalog instead of a hardcoded dict."""
    return {
        "automated": _tier_progress(ACHIEVEMENT_AUTOMATED_THRESHOLDS, automated_achievement_id),
        "rows": _tier_progress(ACHIEVEMENT_ROW_THRESHOLDS, row_achievement_id),
    }


ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _schedule_achievement_toast_hide(ms):
    """The auto-hide delay is scheduled from JS, not Python. This game's
    own no-timer wellbeing constraint (Milestone 7's
    test_nothing_in_the_game_runs_on_a_timer, a literal substring scan of
    this file's own source for the browser's clock-driven timer APIs) bans
    a real timer call from ever appearing here -- the same constraint that
    already pushed the arcade minigame family's real 1-second tick out into
    index.html's own boot script rather than into game.py or minigames.py
    (see CLAUDE.md's Milestone 27 build note). Safe to call from plain
    CPython (this file's own test harness): a missing `js.window` or
    sender function is simply a no-op, the same defensive-import pattern
    `_dispatch_report()` above already uses for its network call."""
    try:
        from js import window  # noqa: PLC0415 — Pyodide-only, deliberately lazy
    except ImportError:
        return
    scheduler = getattr(window, "scheduleAchievementToastHide", None)
    if scheduler is not None:
        scheduler(ms)


def show_achievement_toast(message):
    toast = _element("achievement-toast")
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")
    _schedule_achievement_toast_hide(ACHIEVEMENT_TOAST_DURATION_MS)


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing.
    Never touches the save, and there is no missing-chapter callout (this
    game's no-guilt stance): unreached chapters are simply not shown."""
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


def _maybe_toast_new_achievements():
    """Diffs the currently-earned set against what's already been seen this
    session and toasts anything newly crossed. Called from
    render_achievements(), which already runs on every render() pass, so
    there's no need for a separate call site wired into every place a
    plot can reach Automated (the main practice panel, Review's nudge,
    etc.)."""
    earned_ids = set(achievement_ids_earned())
    _story_reach_all(earned_ids)  # W1: also brings a loaded save's chapters back
    newly_earned_ids = earned_ids - runstate._achievement_ids_seen
    runstate._achievement_ids_seen = earned_ids
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


def on_toggle_achievements(event=None):
    runstate.achievements_open = not runstate.achievements_open
    render()


def _render_achievement_group(container, group):
    for entry in group["earned"]:
        line = document.createElement("p")
        line.className = "achievement-earned"
        line.innerText = "🏆 "
        label = document.createElement("span")
        label.className = "achievement-card-label"  # shared/achievement-share.js reads the name from here
        label.innerText = entry["label"]
        line.appendChild(label)
        line.dataset.achievementId = entry["id"]
        container.appendChild(line)
    if group["next"] is not None:
        line = document.createElement("p")
        line.className = "achievement-next"
        line.innerText = (
            f"Next: {group['next']['label']} ({group['next']['current']} of {group['next']['target']})"
        )
        line.dataset.achievementId = group["next"]["id"]
        container.appendChild(line)
    if not group["earned"] and group["next"] is None:
        line = document.createElement("p")
        line.className = "achievement-empty"
        line.innerText = "Nothing here yet."
        container.appendChild(line)


def render_achievements():
    _maybe_toast_new_achievements()

    panel = _element("achievements-panel")
    toggle = _element("achievements-toggle-button")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if runstate.achievements_open
        else f"\U0001F3C6 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not runstate.achievements_open
    if not runstate.achievements_open:
        return

    panel.innerHTML = ""
    summary = achievements_summary()

    automated_heading = document.createElement("p")
    automated_heading.className = "achievement-heading"
    automated_heading.innerText = "Plots automated"
    panel.appendChild(automated_heading)
    _render_achievement_group(panel, summary["automated"])

    rows_heading = document.createElement("p")
    rows_heading.className = "achievement-heading"
    rows_heading.innerText = "Full weeks automated"
    panel.appendChild(rows_heading)
    _render_achievement_group(panel, summary["rows"])

    # A link out to the hub-wide achievements dashboard (planning/
    # ACHIEVEMENTS-SYSTEM-DESIGN.md §5, and the "roll achievements out
    # everywhere" section of planning/TODO.md). Hub-side script.js
    # registration (GAMES_WITH_ACHIEVEMENTS/GAME_DISPLAY_NAMES) is a
    # separate, shared-file change tracked outside this game's own dispatch.
    hub_link = document.createElement("a")
    hub_link.className = "achievements-hub-link"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each visible achievement row's
    own "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Unlike the other 11 games' full card grid, this
    game's panel only ever shows each tier's earned entries plus its one
    "next" target -- see _render_achievement_group() above -- so most
    achievement ids never appear in the DOM at all here, which is fine:
    the shared hook only ever touches rows it can find via
    data-achievement-id. Absent hook (pytest, or a page without the shared
    script) leaves the rows exactly as rendered above -- same fails-soft
    shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin
# K16: "Per-game in-game changelog panel, for every game"). A quick
# highlights view, not a full duplicate of CLAUDE.md -- same loading
# contract as ACHIEVEMENTS above, reusing the shared _read_json_asset()
# helper this game already uses for the catalog/supplementary-notes files.
# Unlike ACHIEVEMENTS, this is a flat list (no wrapping key) -- see
# changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    return _read_json_asset(CHANGELOG_FILENAME, "CHANGELOG_JSON")


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to this
# game's gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
    CHANGELOG = []


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    render()


def render_changelog():
    # Reuses .dashboard-panel's card and the same one-<p>-per-row idiom the
    # progress dashboard's own mastery/weakest/pattern lists already use
    # (see render_dashboard() above), rather than the two-part
    # "changelog-entry" card the rest of the hub's own K16 dispatches use --
    # internals are free once you're inside a game, and this game already
    # has its own established row idiom worth staying consistent with.
    panel = _element("changelog-panel")
    toggle = _element("changelog-toggle-button")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "📋 What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    # Newest first -- entries are authored newest-first in changelog.json
    # already, but sort defensively so a future out-of-order edit can't
    # silently invert the panel.
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        line = document.createElement("p")
        line.className = "changelog-row"
        line.innerText = f"{entry['date']} — {entry['entry']}"
        panel.appendChild(line)
