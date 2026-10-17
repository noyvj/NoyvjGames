"""The info page, the personal best coastline (localStorage), the What's New changelog and the fish warning banner."""

import json

import info_page
from js import document, setTimeout
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_bridge import _read_local_storage_item, _write_local_storage_item


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Ocean acidification and sea-level rise are two separate "
        "consequences of the same underlying cause — the ocean absorbing "
        "extra CO2 and extra heat — and both show up on a delay: today's "
        "emissions determine damage that doesn't fully land for years. "
        "Tide's delayed-effect ticker and background sea-level timeline "
        "are built around that real lag."
    ),
    "mechanic_tie_in": (
        "The fish-stock crash mechanic mirrors the real acidification "
        "pathway — more absorbed CO2 makes water more acidic, which is "
        "measurably harmful to shellfish and reef-building organisms first."
    ),
    "sources": [
        {
            "label": "NOAA Fisheries — Understanding Ocean Acidification",
            "url": "https://www.fisheries.noaa.gov/insight/understanding-ocean-acidification",
            "note": "Explains the shellfish/reef impact mechanism directly — the real process behind Tide's fish-stock crash.",
        },
        {
            "label": "NASA Sea Level Change Portal — Global Mean Sea Level",
            "url": "https://sealevel.nasa.gov/understanding-sea-level/key-indicators/global-mean-sea-level/",
            "note": "Real satellite-measured sea-level data and rate-of-rise figures, informing the pacing of Tide's background timeline.",
        },
        {
            "label": "NOAA Climate.gov — Climate Change: Global Sea Level",
            "url": "https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level",
            "note": "Explains both causes of sea-level rise (thermal expansion + ice melt) in plain language.",
        },
        {
            "label": "Smithsonian Ocean Portal — Ocean Acidification",
            "url": "https://ocean.si.edu/ocean-life/invertebrates/ocean-acidification",
            "note": "A clear, visual explanation of the acidification chemistry, most accessible of the four sources.",
        },
    ],
}


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


# D13: a per-browser "best coastline saved" personal best -- the highest
# damage_saved() this browser has ever seen, across every session/save on
# this device. Deliberately NOT part of get_state()/the save-code system
# (same distinction Canopy's B14/Thaw's G19 draw): this is a cross-session
# device record, not one save's snapshot.
BEST_COASTLINE_STORAGE_KEY = "tide_best_coastline_saved_v1"

# Z6 (planning/TODO.md "Z. Games"): duration of the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css) --
# matches the CSS animation's own length, same value Canopy/Thaw use.
PERSONAL_BEST_BADGE_MS = 1800


def load_best_coastline_saved():
    raw = _read_local_storage_item(BEST_COASTLINE_STORAGE_KEY)
    if not raw:
        return 0.0
    try:
        return float(json.loads(raw))
    except (ValueError, TypeError):
        return 0.0


runstate.best_coastline_saved = load_best_coastline_saved()


def _maybe_update_best_coastline_saved():
    """Called every render(); bumps + persists the record whenever the
    live session's damage_saved() exceeds it."""
    if runstate.state.keeps_records_out():  # D-5 / GD-5: custom rules and daily runs never set the standard best
        return
    saved = runstate.state.damage_saved()
    if saved > runstate.best_coastline_saved:
        runstate.best_coastline_saved = saved
        _write_local_storage_item(BEST_COASTLINE_STORAGE_KEY, json.dumps(runstate.best_coastline_saved))
        _flash_personal_best_badge()


def _flash_personal_best_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a session beats its stored best.
    Same setTimeout+create_proxy shape as Canopy/Thaw's equivalent."""
    element = document.getElementById("best-coastline-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("best-coastline-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), PERSONAL_BEST_BADGE_MS)


def render_best_coastline_saved():
    element = document.getElementById("best-coastline-display")
    if element is None:
        return
    element.innerText = f"Best coastline saved (this browser): {runstate.best_coastline_saved:.0f} damage avoided"


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above: the boot
# script fetches changelog.json and hands it to Python as a window global
# before this module runs; the pytest harness's fake `js` has no such
# attribute, so this falls through to reading the file straight off disk.
# A flat, hand-written list of highlights pulled from this game's own
# CLAUDE.md milestone table and iteration-pass notes -- not a full
# duplicate of the dev logs, just a quick "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Same defensive posture as ACHIEVEMENTS above: the changelog is additive,
# not core to gameplay, so any loading failure degrades to "no changelog"
# instead of crashing the whole module import. changelog.json is authored
# newest-first already, but sorted defensively here in case a future entry
# is appended out of order.
try:
    CHANGELOG = sorted(
        json.loads(_read_changelog_json())["changelog"],
        key=lambda entry: entry["date"],
        reverse=True,
    )
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "📋 What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)
