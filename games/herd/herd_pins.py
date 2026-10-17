"""The pinned-stat strip (F-16).
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import json

from js import document

import herd_runstate as runstate
from herd_util import _read_local_storage_item, _write_local_storage_item


# ---- F-16 pin-a-stat strip ---------------------------------------------------------------
# Up to three readouts pinned into a sticky strip, so they stay in view while the extras panels are
# open. The choice is a browser preference (localStorage), never part of a save.
PINS_STORAGE_KEY = "herd-pinned-stats"
PIN_MAX = 3
PIN_STATS = {
    "funds": ("Funds", lambda: "unlimited" if runstate.sandbox_active else f"{runstate.farm.funds:.0f}"),
    "income": ("Income per round", lambda: f"{runstate.farm.income_breakdown()['total']:.1f}"),
    "welfare": ("Welfare", lambda: f"{runstate.farm.welfare():.0f}/100"),
    "methane_round": ("Methane per round", lambda: f"{runstate.farm.methane_this_round():.1f}"),
    "methane": ("Total methane", lambda: f"{runstate.farm.methane:.0f}"),
    "score": ("Score", lambda: "not counted" if runstate.sandbox_active else f"{runstate.farm.score():.0f}"),
    "herd": ("Herd", lambda: f"{runstate.farm.herd_size}"),
    "pressure": ("Pressure", lambda: f"{runstate.farm.pressure_fraction() * 100:.0f}% income loss"),
}


def clean_pins(raw):
    """Pin ids from stored or untrusted data: real stats only, no repeats, at most PIN_MAX."""
    if not isinstance(raw, list):
        return []
    pins = []
    for item in raw:
        if isinstance(item, str) and item in PIN_STATS and item not in pins:
            pins.append(item)
    return pins[:PIN_MAX]


def load_pins():
    raw = _read_local_storage_item(PINS_STORAGE_KEY)
    if not raw:
        return []
    try:
        return clean_pins(json.loads(raw))
    except (ValueError, TypeError):
        return []


def set_pin(stat, on):
    """Pins or unpins one stat. Pinning a fourth is refused. Returns True when the pins changed."""
    if stat not in PIN_STATS:
        return False
    if on and stat not in runstate.pinned_stats and len(runstate.pinned_stats) < PIN_MAX:
        runstate.pinned_stats = runstate.pinned_stats + [stat]
    elif not on and stat in runstate.pinned_stats:
        runstate.pinned_stats = [s for s in runstate.pinned_stats if s != stat]
    else:
        return False
    _write_local_storage_item(PINS_STORAGE_KEY, json.dumps(runstate.pinned_stats))
    return True


def pinned_strip_html():
    return "".join(
        f'<span class="pin-chip"><span class="pin-chip-label">{PIN_STATS[stat][0]}</span> '
        f'<span class="pin-chip-value">{PIN_STATS[stat][1]()}</span></span>'
        for stat in runstate.pinned_stats
    )


def render_pins():
    strip = document.getElementById("pinned-strip")
    strip.hidden = not runstate.pinned_stats
    strip.innerHTML = pinned_strip_html()
    full = len(runstate.pinned_stats) >= PIN_MAX
    for stat in PIN_STATS:
        box = document.getElementById(f"pin-{stat.replace('_', '-')}")
        box.checked = stat in runstate.pinned_stats
        box.disabled = full and stat not in runstate.pinned_stats
    document.getElementById("pin-note").innerText = (
        f"{len(runstate.pinned_stats)} of {PIN_MAX} pinned. Untick one to pin another." if full
        else f"{len(runstate.pinned_stats)} of {PIN_MAX} pinned. Pinned stats stay in a strip at the top of the page."
    )


def _make_pin_handler(stat):
    def handler(event=None):
        set_pin(stat, bool(document.getElementById(f"pin-{stat.replace('_', '-')}").checked))
        render_pins()
    return handler
