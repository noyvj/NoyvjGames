"""The session summary, screen-reader announcements, the tab title and favicon, copy as text, and the graph range chips."""

import js as _js
from js import document
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_almanac import almanac_best_line, render_planner
from tide_graphs import _save_graph_prefs, render_graphs
from tide_libraryview import render_library
from tide_rules import GRAPH_RANGES


def update_session_summary_display():
    toggle = document.getElementById("session-summary-toggle-button")
    panel = document.getElementById("session-summary-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Session Summary" if runstate.session_summary_open else "📋 Session Summary"
    panel.hidden = not runstate.session_summary_open
    if not runstate.session_summary_open:
        return
    text_el = document.getElementById("session-summary-text")
    if text_el is not None:
        best_line = almanac_best_line()
        text_el.innerText = runstate.state.session_summary_text() + (" " + best_line if best_line else "")


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line
    ("Tide, 12 seasons, 340 damage taken, ..."). Read by the page's own
    inline script through pyodide.globals when the Copy result button is
    pressed, so it always describes the run as it stands right now."""
    seasons = max(0, runstate.state.season - 1)
    stats = [
        {"n": round(runstate.state.cumulative_damage), "one": "damage taken", "many": "damage taken"},
        {"n": round(runstate.state.damage_saved()), "one": "damage saved by adaptation", "many": "damage saved by adaptation"},
        "tier: " + runstate.state.current_tier()["name"],
    ]
    storms = len(runstate.state.storm_log)
    if storms:
        stats.append({"n": storms, "one": "storm survived", "many": "storms survived"})
    return {
        "game": "Tide",
        "score": seasons,
        "unit": "season" if seasons == 1 else "seasons",
        "stats": stats,
    }


def render_fish_warning_banner():
    """D14: an early-warning banner for a fish-yield crash already locked
    in by acidity that's already in the pipeline -- distinct from the
    ticker's after-the-fact narration, this fires *before* the drop
    lands, using next_season_fish_yield_preview()."""
    banner = document.getElementById("fish-warning-banner")
    if banner is None:
        return
    if runstate.state.fish_warning_active():
        preview = runstate.state.next_season_fish_yield_preview()
        banner.hidden = False
        banner.innerText = (
            f"⚠️ Heads up: fishing yield is on track to fall to about {preview * 100:.0f}% "
            f"next season — acidity already recorded is catching up. "
            "Suggested action: invest in Acidity Reduction now, and expect the dip to last a few seasons."
        )
    else:
        banner.hidden = True


def render_graph_controls():
    for key, label in GRAPH_RANGES:
        button = document.getElementById(f"graph-range-{key}")
        if button is not None:
            button.innerText = label
            button.setAttribute("aria-pressed", "true" if key == runstate.graph_range else "false")
    markers = document.getElementById("graph-markers-toggle")
    if markers is not None:
        markers.innerText = "Series markers: On" if runstate.graph_markers else "Series markers: Off"
        markers.setAttribute("aria-pressed", "true" if runstate.graph_markers else "false")


def _make_graph_range_handler(key):
    def handler(event=None):
        runstate.graph_range = key
        _save_graph_prefs()
        render_graph_controls()
        render_graphs()
        render_library()
        render_planner()
    return handler


# ---- D-7 announcements -------------------------------------------------
def _shared_announce(text):
    """B-7: speak through shared/announcer.js when the page has it (returns True); otherwise the game's own
    live region is used. Never both, so a screen reader does not read a message twice."""
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


def announce(text):
    """Writes into the polite live region screen readers watch."""
    if text and _shared_announce(text):
        return
    region = document.getElementById("season-announcer")
    if region is not None:
        region.innerText = text


# ---- D-24 tab title and favicon ----------------------------------------


def _favicon_data_uri(kind):
    """A small wave badge; a warning adds an amber circle, a storm a red
    square (a different shape, so the two are not told apart by hue alone)."""
    marker = ""
    if kind == "warning":
        marker = '<circle cx="23" cy="9" r="7" fill="#f5a623" stroke="#fff" stroke-width="1.5"/>'
    elif kind == "storm":
        marker = '<rect x="16" y="2" width="14" height="14" fill="#e03e3e" stroke="#fff" stroke-width="1.5"/>'
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="7" fill="#0e5a8a"/>'
        '<path d="M3 20 Q8 14 13 20 T23 20 T31 20 V30 H3Z" fill="#7fd4ee"/>'
        f"{marker}</svg>"
    )
    return "data:image/svg+xml," + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23").replace('"', "'")


def tab_status():
    """(title, favicon kind) for the current state."""
    title = f"Tide S{runstate.state.season}"
    reasons = runstate.state.attention_reasons()
    kinds = [kind for kind, _text in reasons]
    if "storm" in kinds:
        return title + " - storm forecast", "storm"
    if "fish" in kinds:
        return title + " - fish warning", "warning"
    if "heritage" in kinds:
        return title + " - heritage at risk", "warning"
    return title, "normal"


def update_tab_status():
    title, kind = tab_status()
    try:
        document.title = title
    except Exception:
        pass
    query = getattr(document, "querySelector", None)
    if query is None:
        return
    link = query('link[rel="icon"]')
    if link is None:
        return
    if runstate._FAVICON_ORIGINAL is None:
        runstate._FAVICON_ORIGINAL = link.href
    link.href = runstate._FAVICON_ORIGINAL if kind == "normal" else _favicon_data_uri(kind)


# ---- D-18 copy as text -------------------------------------------------
_copy_proxies = {}


def _copy_to_clipboard(text, on_done=None, on_fail=None):
    """True when a clipboard write was started. The browser promise's own
    outcome is reported through on_done/on_fail when they are given."""
    navigator = getattr(_js, "navigator", None)
    clipboard = getattr(navigator, "clipboard", None) if navigator is not None else None
    if clipboard is None:
        return False
    try:
        promise = clipboard.writeText(text)
        if on_done is not None and on_fail is not None and hasattr(promise, "then"):
            for name, handler in (("done", on_done), ("fail", on_fail)):
                _copy_proxies[name] = create_proxy(handler)
            promise.then(_copy_proxies["done"], _copy_proxies["fail"])
        return True
    except Exception:
        return False


def _show_copy_fallback(text):
    status = document.getElementById("copy-text-status")
    area = document.getElementById("copy-text-area")
    if area is not None:
        area.hidden = False
        area.value = text
    if status is not None:
        status.innerText = "Could not copy automatically. Select the text below and copy it yourself."
