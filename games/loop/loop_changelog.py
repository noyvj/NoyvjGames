"""The in-game 'What's New' changelog panel (K16)."""

import json

from js import document

import loop_runstate as runstate


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as the achievements catalog above
# -- a flat JSON list fetched into the Pyodide boot sequence and handed to
# Python as a window global (see index.html), rendered into a
# hidden-until-opened panel. Unlike achievements.json this catalog isn't a
# set of checkable conditions -- it's just curated highlight text -- so
# there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
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


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS above, since a "what's
# new" panel is additive, not core to Loop's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []


def on_toggle_changelog(event=None):
    runstate.changelog_open = not runstate.changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

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
