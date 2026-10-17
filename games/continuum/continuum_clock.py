"""The season clock: season length, speed buttons and the clock readout. The tick itself is in continuum_advance."""

from js import document

import continuum_runstate as runstate
from continuum_base import SEASON_SECONDS, SPEEDS


# ===========================================================================
# U1: tick-based play. Seasons now pass on their own instead of waiting for an
# Advance Season button (which is gone). The pace is real time: a season takes
# SEASON_SECONDS[era] seconds at 1x (slower in later eras, which have more to
# weigh), divided by the chosen speed. Deliberately conservative:
#   - a settlement (and every load) starts PAUSED, so nothing happens before
#     you have read anything; speed is never saved;
#   - the clock only runs while the page is open and visible (index.html's
#     ticker skips hidden tabs and clamps each step), so nothing piles up
#     while you are away, matching the hub's no-idle-timer stance;
#   - it never runs during a Look Back (a revisit is a frozen view).
# `on_advance_season()` remains the one place a season actually happens.
# ===========================================================================


def season_length():
    return SEASON_SECONDS.get(runstate.state.era, 10.0)


def set_speed(speed):
    if speed not in SPEEDS:
        return False
    runstate.sim_speed = speed
    render_clock()
    return True


def render_clock():
    labels = {0: "pause", 1: "1x", 2: "2x", 4: "4x"}
    for speed, key in labels.items():
        button = document.getElementById(f"speed-{key}-button")
        active = speed == runstate.sim_speed
        if active:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")
        button.setAttribute("aria-pressed", "true" if active else "false")
    fraction = min(1.0, runstate.season_progress / season_length())
    document.getElementById("season-progress-fill").style.width = f"{fraction * 100:.0f}%"
    if runstate.campaign.revisiting:
        text = "Looking back \u2014 time is held while you view a past era."
    elif runstate.sim_speed == 0:
        text = "Paused \u2014 choose 1x, 2x or 4x to let seasons pass."
    else:
        remaining = max(0.0, (season_length() - runstate.season_progress) / runstate.sim_speed)
        text = f"Running at {runstate.sim_speed}x \u2014 next season in {remaining:.0f}s."
    document.getElementById("season-clock-display").innerText = text


def _make_speed_handler(speed):
    def handler(event=None):
        set_speed(speed)
    return handler


def current_sim_speed():
    """The clock speed right now. The page asks for it by name (pyodide.globals.get("current_sim_speed")) because sim_speed lives
    in continuum_runstate, so a copy of the variable read from game.py's globals would go stale."""
    return runstate.sim_speed
