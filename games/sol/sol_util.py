"""Small shared helpers used everywhere: the toast, localStorage reads and writes, time and number formatting, DOM element makers, floating sparks, planet lists, view hiding and a few small pure checks."""

import json
import math

import challenges
from js import document, setTimeout
from pyodide.ffi import create_proxy

import sol_runstate as runstate
from sol_rules import (
    GAS_GIANT_BODIES, PLANETS, PLANET_DISPLAY_NAMES, SCARCITY_OFF_KEYS, TERRAFORM_MAX, TICK_INTERVAL_MS,
    TODAY_OVERRIDE, planet_state,
)


def _dom_id(planet, suffix):
    # Earth's ids are unprefixed (predate multi-planet support); every other
    # real economy gets a "<planet>-" prefix.
    prefix = "" if planet == "Earth" else f"{planet.lower()}-"
    return f"{prefix}{suffix}"


def clamp(value, low, high):
    return max(low, min(high, value))


def _total_trade_routes():
    return sum(sum(state["trade_routes"].values()) for state in planet_state.values())


def _terraformed_planet_count():
    return sum(1 for state in planet_state.values() if state["terraform_progress"] >= TERRAFORM_MAX)


def _display_toast(message):
    # Shared by both the achievement-unlock toast and the welcome-back toast
    # (A3) -- same fixed-position element, same show-then-auto-hide timing,
    # just different message text. A second toast firing before the first's
    # timeout clears simply replaces the visible text and restarts the
    # timer's effect (the old timeout still fires and finds the toast
    # already hidden-by-the-new-one's-own-timeout is harmless: both timeouts
    # just set hidden = True).
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


def _setting_on(key):
    if runstate._scarcity is not None and key in SCARCITY_OFF_KEYS:
        return False  # a Scarcity Run is played on the same rules by everyone
    return _read_local_storage_item(key) != "off"


def _split_time(ticks):
    return _format_duration(ticks * (TICK_INTERVAL_MS / 1000))


def _split_delta(ticks, best_ticks):
    """Signed difference as text ('+0m 12s', '-5s', 'same'), never colour alone."""
    diff = (ticks - best_ticks) * (TICK_INTERVAL_MS / 1000)
    if abs(diff) < 0.5:
        return "same as best"
    return ("+" if diff > 0 else "-") + _format_duration(abs(diff))


def split_label(key):
    return "Whole system terraformed" if key == "full" else PLANET_DISPLAY_NAMES.get(key, key)


def _format_duration(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _hide_all_views():
    document.getElementById("earth-view").hidden = True
    document.getElementById("mars-view").hidden = True
    document.getElementById("moon-view").hidden = True
    document.getElementById("venus-view").hidden = True
    document.getElementById("asteroidbelt-view").hidden = True
    document.getElementById("pluto-view").hidden = True
    document.getElementById("jupitermoons-view").hidden = True
    document.getElementById("saturnmoons-view").hidden = True
    document.getElementById("away-view").hidden = True


def press_feedback(button):
    # Called on essentially every player interaction (every click, buy,
    # travel, governor, and destination-cycle button), so the one-shot
    # setTimeout proxy created here must be destroyed once it fires —
    # otherwise each press leaks a PyProxy for the rest of the session,
    # a slow memory leak that never gets cleaned up on its own since
    # Pyodide can't garbage-collect a JsProxy-wrapped Python callable
    # until .destroy() is called explicitly.
    button.classList.add("pressed")

    def _clear(*args):
        button.classList.remove("pressed")
        proxy.destroy()
    proxy = create_proxy(_clear)
    setTimeout(proxy, 120)


def _fresh_planet_state(planet):
    fresh = {
        "resource_count": 0.0,
        "generator_count": 0,
        "recycler_count": 0,
        "ecology_health": 100.0,
        "trade_routes": {},
        "trade_destination": None,
        "terraform_progress": 0.0,
        "governed_resource_generated": 0.0,
        "governor_personality": "default",
        "specialization": None,
        "player_actions": 0,
    }
    if planet in GAS_GIANT_BODIES:
        fresh["sky_city_count"] = 0
    return fresh


# ===========================================================================
# Session additions (planning/TODO.md "Per-game: SOL": A2, A4-A9, A12-A21,
# A23, A24, A27, A28, A30). Panels that carry BUTTONS (overview, build plan,
# prestige tree) use one delegated listener bound once in setup() and read
# `data-*` attributes off event.target, and are only rebuilt when their
# structure actually changes -- never every tick -- so a click can never land
# on a button that was just swapped out from under the cursor.
# ===========================================================================


def _target_attr(event, name):
    """Reads a data-* attribute off a delegated click's target, tolerating a
    text-node/None target (returns None rather than raising)."""
    try:
        target = event.target
        if target is None:
            return None
        value = target.getAttribute(name)
        return None if value is None else str(value)
    except (AttributeError, TypeError):
        return None


def _make_button(text, attrs, tip=None, selected=False, disabled=False):
    button = document.createElement("button")
    button.type = "button"
    button.className = "secondary mini-button" + (" selected" if selected else "")
    button.innerText = text
    for key, value in attrs.items():
        button.setAttribute(key, value)
    if tip:
        button.title = tip
    button.disabled = disabled
    return button


def _make_text(class_name, text, tag="p"):
    element = document.createElement(tag)
    element.className = class_name
    element.innerText = text
    return element


# --- A12 / A30: floating spark on a manual click, floating icon on a build ---
_MAX_FLOATERS = 14


def _spawn_floater(anchor, glyph, css_class, event=None):
    if runstate._active_floaters >= _MAX_FLOATERS:
        return
    try:
        rect = anchor.getBoundingClientRect()
        x = rect.left + rect.width / 2
        y = rect.top + rect.height / 2
        if event is not None:
            client_x = getattr(event, "clientX", None)
            client_y = getattr(event, "clientY", None)
            if client_x and client_y:
                x, y = client_x, client_y
        layer = document.getElementById("spark-layer")
        floater = document.createElement("span")
    except (AttributeError, TypeError, KeyError):
        return  # no layout/DOM available (headless): visual polish only, skip silently
    floater.className = f"floater {css_class}"
    floater.innerText = glyph
    floater.style.left = f"{x}px"
    floater.style.top = f"{y}px"
    layer.appendChild(floater)
    runstate._active_floaters += 1

    def _remove(*args):
        runstate._active_floaters = max(0, runstate._active_floaters - 1)
        layer.removeChild(floater)
        proxy.destroy()

    proxy = create_proxy(_remove)
    setTimeout(proxy, 700)


def _overview_planets():
    return [p for p in PLANETS if p == "Earth" or p in runstate.unlocked_bodies]


def _read_local_storage_item(key):
    """Broad except on the actual read is deliberate: a real browser can
    refuse localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, not core gameplay,
    so it degrades to "nothing stored" rather than crashing the toast."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 — see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 — see _read_local_storage_item's docstring
        pass


def _mmss(ticks):
    seconds = int(math.ceil(ticks * TICK_INTERVAL_MS / 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _clean_ids(raw, known):
    cleaned = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item in known and item not in cleaned:
                cleaned.append(item)
    return cleaned


def _today_utc():
    """The view's clock: today's UTC date as YYYY-MM-DD, or None where there is no clock (the tests). The only
    place in the Scarcity Run that asks what day it is; everything else takes the date as an argument."""
    if TODAY_OVERRIDE:
        return TODAY_OVERRIDE
    try:
        from js import Date  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        text = str(Date.new().toISOString())[:10]
        return text if challenges.valid_date(text) else None
    except Exception:  # noqa: BLE001 -- no clock available: callers treat None as "no date"
        return None


def _read_json_item(key):
    raw = _read_local_storage_item(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None
