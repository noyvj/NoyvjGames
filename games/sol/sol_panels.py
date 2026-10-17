"""The What's New changelog panel and the Governor report."""

import json
import math

from js import document

import sol_runstate as runstate
from sol_doctrines import doctrine_report_line, doctrines_unlocked
from sol_econ import production_multiplier
from sol_rhythm import governor_mood
from sol_rules import PLANETS, PLANET_DISPLAY_NAMES, planet_state


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above (and Le
# Champ de Mots' own precedent): the boot script fetches changelog.json and
# hands it to Python as a window global before this module runs; the
# pytest harness's fake `js` has no such attribute, so this falls through
# to reading the file straight off disk. A flat, hand-written list of
# highlights pulled from CLAUDE.md's own milestone table and build notes —
# not a full duplicate of the dev logs, just a quick "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

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


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if runstate.changelog_open else "📋 What's New"
    panel.hidden = not runstate.changelog_open
    if not runstate.changelog_open:
        return

    panel.innerHTML = ""
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


# ===========================================================================
# Governor Report (A11) — a visible "governor efficiency" readout.
# ===========================================================================


def update_governor_report_display():
    toggle = document.getElementById("governor-report-toggle-button")
    panel = document.getElementById("governor-report-panel")
    toggle.innerText = "Hide Governor Report" if runstate.governor_report_open else "🎛️ Governor Report"
    panel.hidden = not runstate.governor_report_open
    if not runstate.governor_report_open:
        return

    panel.innerHTML = ""

    intro = document.createElement("p")
    intro.className = "governor-report-intro"
    intro.innerText = (
        f"Priority: {runstate.governor_priority.title()} · Budget: {round(runstate.governor_budget_pct)}% "
        "of each governed world's own resources"
    )
    panel.appendChild(intro)

    governed_planets = [planet for planet in PLANETS if planet != runstate.current_planet]
    total_generated = 0.0
    for planet in governed_planets:
        state = planet_state[planet]
        generated = state["governed_resource_generated"]
        total_generated += generated

        card = document.createElement("div")
        card.className = "governor-report-card"

        name = document.createElement("p")
        name.className = "governor-report-card-name"
        name.innerText = PLANET_DISPLAY_NAMES.get(planet, planet)
        card.appendChild(name)

        efficiency = document.createElement("p")
        efficiency.className = "governor-report-card-efficiency"
        if state["generator_count"] == 0:
            efficiency.innerText = "No automation yet"
        else:
            efficiency.innerText = f"Efficiency: {round(production_multiplier(planet) * 100)}%"
        card.appendChild(efficiency)

        generated_el = document.createElement("p")
        generated_el.className = "governor-report-card-generated"
        generated_el.innerText = (
            f"Generated while governed: {math.floor(generated + 1e-9)} {PLANETS[planet]['resource_name']}"
        )
        card.appendChild(generated_el)

        mood = document.createElement("p")
        mood.className = "governor-report-card-mood"
        mood.innerText = f"Mood: {governor_mood(planet)}"
        card.appendChild(mood)

        if doctrines_unlocked():
            doctrine_line = document.createElement("p")
            doctrine_line.className = "governor-report-card-doctrine"
            doctrine_line.innerText = doctrine_report_line(planet)
            card.appendChild(doctrine_line)

        panel.appendChild(card)

    if not governed_planets:
        empty = document.createElement("p")
        empty.className = "governor-report-empty"
        empty.innerText = "No other worlds exist yet for the Governor to manage."
        panel.appendChild(empty)
        return

    total = document.createElement("p")
    total.className = "governor-report-total"
    total.innerText = f"Total generated across every governed world: {math.floor(total_generated + 1e-9)}"
    panel.appendChild(total)
