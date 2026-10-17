"""The What's New changelog panel, the weather log panel and the Info Page toggle.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import json

import info_page
from js import document

import grid_runstate as runstate
from grid_savegame import load_report_text
from grid_trend import INFO_PAGE


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above (and SOL's
# reference integration): the boot script fetches changelog.json and hands
# it to Python as a window global before this module runs; the pytest
# harness's fake `js` has no such attribute, so this falls through to
# reading the file straight off disk. A flat, hand-written list of
# highlights pulled from this game's own CLAUDE.md milestone table and
# build notes — not a full duplicate of the dev logs, just a quick
# "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Same defensive posture as ACHIEVEMENTS above: the changelog is additive,
# not core to gameplay, so any loading failure degrades to "no changelog"
# instead of crashing the whole module import.
try:
    CHANGELOG = json.loads(_read_changelog_json())["changelog"]
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "📋 What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    note_text = load_report_text()
    if note_text:
        note = document.createElement("p")
        note.className = "changelog-load-note"
        note.innerText = note_text
        panel.appendChild(note)
    # changelog.json is authored newest-first already, so no re-sort needed
    # here — same "trust the JSON's own order" posture ACHIEVEMENTS takes.
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


def on_toggle_weather_log(event=None):
    runstate.weather_log_open = not runstate.weather_log_open
    update_weather_log_display()


def update_weather_log_display():
    toggle = document.getElementById("weather-log-toggle-button")
    panel = document.getElementById("weather-log-panel")
    toggle.innerText = "Hide Weather Log" if runstate.weather_log_open else "🌦️ Weather Log"
    panel.hidden = not runstate.weather_log_open
    if not runstate.weather_log_open:
        return

    panel.innerHTML = ""
    if not runstate.state.weather_log:
        empty = document.createElement("p")
        empty.className = "weather-log-empty"
        empty.innerText = (
            "No weather-variability effects recorded yet -- turn on Weather Variability "
            "above and advance a round with renewables built to see entries here."
        )
        panel.appendChild(empty)
        return

    # Newest first, matching the achievements/changelog panels' convention.
    for message in reversed(runstate.state.weather_log):
        row = document.createElement("p")
        row.className = "weather-log-entry"
        row.innerText = message
        panel.appendChild(row)


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, runstate.info_page_open)


def on_toggle_info_page(event=None):
    runstate.info_page_open = info_page.toggle(runstate.info_page_open)
    render_info_page()
