"""Advancing a round: the round animation (C-23), auto-advance, the round recap panel and their render.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document, setTimeout
from pyodide.ffi import create_proxy

import grid_runstate as runstate
from grid_announce import round_recap_text
from grid_callouts import _check_renewable_milestone


# ---- C-23 round-advance animation ------------------------------------------------------------------------------------
# A short (under one second) picture after Advance Round: a sun that crosses its arc if the grid has solar, wind streaks if
# it has wind (one per few turbines, at most four), and the demand curve drawing itself. It only plays what the grid
# really has, never changes a number, and is purely decoration: it is hidden from screen readers (the round announcement
# says it all), switched off with the Settings checkbox, and not shown at all under Reduce motion (CSS).
ROUND_ANIMATION_MS = 900
ROUND_ANIMATION_WIDTH = 280
ROUND_ANIMATION_HEIGHT = 44
ROUND_ANIMATION_MAX_STREAKS = 4
ROUND_ANIMATION_POINTS = 10


def round_animation_parts():
    """What the animation would show for the grid as it stands: which scenes and how many streaks."""
    wind_units = runstate.state.plant_counts["wind"]
    return {
        "sun": runstate.state.plant_counts["solar"] > 0,
        "wind": wind_units > 0,
        "streaks": min(ROUND_ANIMATION_MAX_STREAKS, 1 + (wind_units - 1) // 3) if wind_units > 0 else 0,
        "curve": len(runstate.state.demand_history) >= 2,
    }


def round_animation_svg():
    parts = round_animation_parts()
    w, h = ROUND_ANIMATION_WIDTH, ROUND_ANIMATION_HEIGHT
    out = []
    if parts["sun"]:
        out.append(
            f'<path d="M 12 {h - 6} Q {w / 4} -18 {w / 2 - 20} {h - 6}" class="ra-arc" pathLength="1" />'
            f'<circle cx="12" cy="{h - 6}" r="5" class="ra-sun" />'
        )
    if parts["wind"]:
        for i in range(parts["streaks"]):
            y = 8 + i * 8
            out.append(
                f'<line x1="{w / 2 + 6}" y1="{y}" x2="{w / 2 + 46}" y2="{y}" class="ra-streak" '
                f'style="animation-delay:{i * 0.1:.1f}s" />'
            )
    if parts["curve"]:
        series = runstate.state.demand_history[-ROUND_ANIMATION_POINTS:]
        lo, hi = min(series), max(series)
        span = (hi - lo) or 1.0
        x0, x1 = w / 2 + 60, w - 6
        pts = " ".join(
            f"{x0 + (x1 - x0) * i / (len(series) - 1):.1f},{h - 6 - (h - 14) * (v - lo) / span:.1f}"
            for i, v in enumerate(series)
        )
        out.append(f'<polyline points="{pts}" class="ra-demand" pathLength="1" />')
    if not out:
        return ""
    return f'<svg viewBox="0 0 {w} {h}" class="round-animation-svg" aria-hidden="true" focusable="false">{"".join(out)}</svg>'


def _play_round_animation():
    """Shows the picture for ROUND_ANIMATION_MS. The last advance wins if two come close together."""
    box = document.getElementById("round-animation")
    svg = round_animation_svg() if runstate.prefs["round_animation"] else ""
    if not svg:
        box.hidden = True
        box.innerHTML = ""
        return
    runstate._round_animation_token += 1
    token = runstate._round_animation_token
    box.innerHTML = svg
    box.hidden = False

    def _hide(*args):
        if token == runstate._round_animation_token:
            box.hidden = True
            box.innerHTML = ""
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, ROUND_ANIMATION_MS)


def render_round_animation_setting():
    document.getElementById("pref-round-animation").checked = runstate.prefs["round_animation"]
    if not runstate.prefs["round_animation"]:
        document.getElementById("round-animation").hidden = True


# GC-17 -- auto-advance: play up to AUTO_ADVANCE_ROUNDS rounds in one click,
# stopping early at the first disruption, aging breakdown or policy-lever
# offer, so there is always a pause at the moments that call for a decision.
# No builds, retires or maintenance happen in between (that is the point:
# "let it run"), and an open policy offer must be answered first.
AUTO_ADVANCE_ROUNDS = 5


def auto_advance(max_rounds=AUTO_ADVANCE_ROUNDS, **rngs):
    """Advance up to max_rounds rounds. Returns (rounds_played, message).
    rngs are passed straight to GridState.advance_round (tests use them)."""
    if runstate.state.policy_lever_available:
        return 0, "A policy lever is waiting for your decision first."
    if runstate.state.grant_offer is not None:
        return 0, "A grant offer is waiting for your decision first."
    played = 0
    reason = f"Played all {max_rounds} rounds with nothing needing a decision."
    for _ in range(max_rounds):
        runstate.state.advance_round(**rngs)
        played += 1
        _check_renewable_milestone()
        if runstate.state.last_event is not None:
            reason = "Stopped: a disruption hit."
            break
        if runstate.state.last_aging_event is not None:
            reason = "Stopped: an aging breakdown took a plant offline."
            break
        if runstate.state.policy_lever_available:
            reason = "Stopped: a policy lever is on offer."
            break
        if runstate.state.grant_offer is not None:
            reason = "Stopped: a grant offer is waiting."
            break
    return played, f"Auto-advanced {played} round(s). {reason}"


def render_auto_advance():
    button = document.getElementById("auto-advance-button")
    button.innerText = f"Auto-advance up to {AUTO_ADVANCE_ROUNDS} rounds"
    button.disabled = runstate.state.policy_lever_available or runstate.state.grant_offer is not None
    button.title = (
        "Answer the policy lever or grant on offer first."
        if runstate.state.policy_lever_available or runstate.state.grant_offer is not None
        else "Plays rounds back to back with no building in between. Stops at the first disruption, "
        "aging breakdown or policy offer."
    )
    status = document.getElementById("auto-advance-status")
    status.innerText = runstate.auto_advance_message
    status.hidden = not runstate.auto_advance_message


def render_round_recap():
    summary, details = round_recap_text()
    document.getElementById("round-recap-summary").innerText = summary
    document.getElementById("round-recap-body").innerText = details
