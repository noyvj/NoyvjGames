"""Comfort features: the slow-computer guard, the coach hints and the while-away chip."""

import time

from js import document

import canopy_runstate as runstate
from canopy_helpers import _announce, _el, plot_coordinate_label, ui_pref
from canopy_rules import BARE, SEASON_CYCLE_TICKS, TICK_INTERVAL_MS
from canopy_valuation import standing_forest_value, state_breakdown
from canopy_worldvars import UI_PREF_COACH


# B-30 (2026-10-09): a performance guard. When ticks arrive much later than scheduled (a slow device or a busy
# tab) the decorative effects (wildlife flutter, value pops, leaf bursts) switch off until the loop is steady
# again, and a small indicator says so. Gameplay and the tick maths are untouched.
PERF_LAG_FACTOR = 2.5  # a gap this many times the tick interval counts as lag
PERF_STRIKES_TO_THROTTLE = 3
PERF_STEADY_TICKS_TO_RECOVER = 30


def update_perf_guard(gap_seconds):
    """Feeds one measured gap between ticks; returns True when the guard's state changed."""
    lagging = gap_seconds > PERF_LAG_FACTOR * TICK_INTERVAL_MS / 1000
    before = runstate.perf_mode
    if lagging:
        runstate._perf_strikes += 1
        runstate._perf_steady = 0
        if runstate._perf_strikes >= PERF_STRIKES_TO_THROTTLE:
            runstate.perf_mode = True
    else:
        runstate._perf_steady += 1
        if runstate._perf_steady >= PERF_STEADY_TICKS_TO_RECOVER:
            runstate.perf_mode = False
            runstate._perf_strikes = 0
    return runstate.perf_mode != before


def _note_tick_clock():
    """Called once per tick: measures the gap since the previous tick, ignoring gaps while the tab was hidden or paused."""
    now = time.time()
    previous, runstate._last_tick_clock = runstate._last_tick_clock, now
    if previous is None or getattr(document, "visibilityState", "visible") == "hidden":
        return
    if update_perf_guard(now - previous):
        render_perf_indicator()


def render_perf_indicator():
    element = _el("perf-indicator")
    root = getattr(document, "documentElement", None)
    if root is not None and hasattr(root, "setAttribute"):
        root.setAttribute("data-perf-mode", "on" if runstate.perf_mode else "off")
    if element is not None:
        element.hidden = not runstate.perf_mode
        element.innerText = "Performance mode: effects are paused while the game catches up" if runstate.perf_mode else ""


# Merges a loaded save onto the live state key-by-key, falling back to the
# current live value for any key the save doesn't carry, rather than bare
# `data["key"]` indexing or a wholesale replace. A save missing a field is
# not necessarily corrupt -- every field here (`biodiversity`,
# `pending_stakeholder_request`, `info_page_open`, ...) was added in a later
# milestone/pass than the one before it, so a save written before that pass
# legitimately lacks the key. Bare indexing would crash the next render/tick
# with a KeyError on exactly that (very real) forward-compatibility case --
# the same bug class found and fixed across nearly every other game in this
# hub (see BCM114-DEV-LOG.md's 2026-09-02 entries).
# B-27 (2026-10-09): opt-in Coach hints in the report card. Plain notes that read the session; they never block
# play (no dialogs), can be dismissed, and are off until the player turns them on in Settings.
COACH_MAX_HINTS = 3
_coach_dismissed = set()


def coach_hints():
    """[(hint id, text)] for what the session shows right now, minus anything already dismissed."""
    hints = []
    worst = max(runstate.plots, key=lambda p: p.clear_count, default=None)
    if worst is not None and worst.clear_count >= 3:
        pct = round(worst.productivity_multiplier() * 100)
        hints.append((
            f"repeat-clear-{worst.index}",
            f"{plot_coordinate_label(worst.index)} has been cleared {worst.clear_count} times and its soil is now at {pct}%. "
            "Soil never recovers, so a plot that has been cleared this often grows more slowly for the rest of the session.",
        ))
    low = [p for p in runstate.plots if p.productivity_multiplier() < 0.6 and p is not worst]
    if low:
        hints.append((
            "soil-low",
            f"{len(low)} other plot{'s' if len(low) != 1 else ''} have soil below 60%. Leaving them standing costs nothing, "
            "but each further clear lowers it again.",
        ))
    counts = state_breakdown()
    if counts[BARE] >= 3 and runstate.total_replants == 0:
        hints.append((
            "replant-first",
            f"{counts[BARE]} plots are bare and nothing has been replanted yet. Replanting restarts growth there "
            "(it does not restore soil quality).",
        ))
    if runstate.community_relations < 30:
        hints.append((
            "relations-low",
            f"Community relations are at {runstate.community_relations}/100. Granting a request or accepting a replanting grant raises them.",
        ))
    return [h for h in hints if h[0] not in _coach_dismissed][:COACH_MAX_HINTS]


def render_coach_hints():
    panel = _el("coach-hints-panel")
    text_el = _el("coach-hints")
    if panel is None or text_el is None:
        return
    hints = coach_hints() if ui_pref(UI_PREF_COACH) == "true" else []
    panel.hidden = not hints
    text_el.innerText = "\n".join("\u2022 " + t for _i, t in hints)


def on_dismiss_coach_hints(event=None):
    for hint_id, _t in coach_hints():
        _coach_dismissed.add(hint_id)
    render_coach_hints()


# B-22 (2026-10-09): a "while away" catch-up chip. When the tab comes back after being hidden and the
# forest really advanced meanwhile (only possible when the player has turned off pausing while hidden, or the
# browser kept ticking), say what changed instead of letting the numbers jump silently. It reads the game's own
# tick counter, so it does not depend on the tick speed. With the default pause-when-hidden nothing advances,
# so no chip appears.
AWAY_MIN_SECONDS = 10


def away_snapshot():
    return {
        "value": standing_forest_value(),
        "ticks": runstate._session_ticks,
        "seasons": runstate.forest_tick // SEASON_CYCLE_TICKS,
    }


def _format_away_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} s"
    minutes, rest = divmod(seconds, 60)
    return f"{minutes} min" if rest == 0 else f"{minutes} min {rest} s"


def away_summary(before, after, seconds):
    """The chip text, or "" when there is nothing to say (away too briefly, or the game did not advance)."""
    if seconds < AWAY_MIN_SECONDS or after["ticks"] <= before["ticks"]:
        return ""
    delta = after["value"] - before["value"]
    ticks = after["ticks"] - before["ticks"]
    seasons = after["seasons"] - before["seasons"]
    parts = [f"standing value {delta:+.1f}", f"{ticks} tick{'s' if ticks != 1 else ''}"]
    if seasons > 0:
        parts.append(f"{seasons} season change{'s' if seasons != 1 else ''}")
    return f"While you were away ({_format_away_duration(seconds)}): " + ", ".join(parts) + "."


def show_away_chip(text):
    element = _el("away-chip")
    if element is None:
        return
    if text:
        element.innerText = text + " (click to dismiss)"
        element.hidden = False
        _announce(text)
    else:
        element.hidden = True


def on_visibility_change(event=None):
    if getattr(document, "visibilityState", "visible") == "hidden":
        runstate._away_snapshot = away_snapshot()
        runstate._away_started_at = time.time()
        return
    if runstate._away_snapshot is None:
        return
    seconds = time.time() - runstate._away_started_at if runstate._away_started_at is not None else 0
    text = away_summary(runstate._away_snapshot, away_snapshot(), seconds)
    runstate._away_snapshot = None
    runstate._away_started_at = None
    show_away_chip(text)


def on_dismiss_away_chip(event=None):
    show_away_chip("")
