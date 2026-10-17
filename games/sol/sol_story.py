"""The achievements catalog (read from achievements.json) and the captain's story log."""

import json

from js import document

import sol_runstate as runstate
from sol_rules import RUMOR_BY_ID


#
# Every achievement's earned status is a pure function of state that already
# exists elsewhere in this module (planet_state, unlocked_bodies,
# completed_tiers, ...), recomputed fresh on every call — never a separately
# hand-maintained "earned" flag that could drift out of sync with the state
# that actually justifies it (same discipline Le Champ de Mots' own
# achievements established: "derive, don't track"). Two small exceptions
# needed one new piece of genuinely new tracked state each, both added
# defensively (safe default, merged in on load, never crashes an older save
# missing the field):
#
# - `visited_bodies` just below: SOL has no existing record of which worlds
#   a player has ever physically traveled to (current_planet only remembers
#   *where you are now*, and unlocked_bodies means research access, not an
#   actual visit — a player can unlock every Far Body and still never have
#   flown to one), so two achievements here ("Off-World", "Grand Tour")
#   genuinely need it.
# - `governor_purchase_count`, defined next to `governor_tick_count` at the
#   top of this module and incremented inside governor_step()'s own buy
#   branches: `governor_tick_count` increments the instant ANY other planet
#   exists to govern, which is true from the very first tick of a brand-new
#   game — it measures ticks elapsed, not the governor having actually
#   bought anything. "Governor Appointed" needs the latter, so it checks
#   `governor_purchase_count` instead — caught during this feature's own
#   live verification pass, where a fresh, untouched game showed the
#   achievement already earned after under a second of real time.
#
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract Le Champ de Mots' game.py established for its
    own static JSON assets (see that game's `_read_json_asset()`): the
    page's boot script fetches achievements.json and hands it to Python as
    a window global before this file runs; the pytest harness's fake `js`
    module simply has no such attribute, so this falls through to reading
    the file straight off disk, which keeps the module importable outside
    a real browser."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per Le Champ de Mots' own live-incident writeup: the real
# Pyodide runtime executes this file's fetched text via
# `pyodide.runPythonAsync(code)`, which never defines `__file__` the way a
# normal file-based import does -- if `_read_achievements_json()`'s
# window-global read ever comes back empty (a boot-script regression, a
# renamed global, a fetch failure), its filesystem fallback crashes with a
# bare, uncaught `NameError` that takes down this ENTIRE module import,
# not just achievements -- exactly the bug that silently broke Le Champ de
# Mots' whole page for every player until it was diagnosed live. Achievements
# are additive, not core to SOL's own gameplay, so this degrades to "no
# achievements catalog" instead, the same posture that game's own
# supplementary-notes loading now takes.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []


# ===========================================================================
# A25 -- the captain's log: a light narrative thread through the run. Every
# first arrival at a world and every achievement earned adds one line to a log
# (recorded whether or not story text is showing, so switching the "Story"
# pill on later reveals the whole history). The latest line sits under the title
# as a banner and the full log is a collapsible list; both are listed as story
# elements for shared/story-toggle.js, so the existing Story pill turns them on
# and off. The lines are the achievements' own descriptions plus one short
# arrival line per world; nothing here changes any number or unlock.
# ===========================================================================
STORY_LOG_MAX = 80
STORY_ARRIVAL_LINES = {
    "Earth": "Log opened. One planet, one pile of iron, and a long way to go.",
    "Mars": "Mars: red dust, thin air, and the first place that feels like somewhere else.",
    "Moon": "The Moon: quiet, close, and a good place to keep the ledger honest.",
    "Venus": "Venus: hot enough to teach patience, thick enough to hide a lot of possibilities.",
    "AsteroidBelt": "The Belt: no ground to stand on, just rock to mine and a lot of room.",
    "Pluto": "Pluto: the edge of the map, cold and slow, and yours anyway.",
    "JupiterMoons": "Jupiter's moons: a small system inside the system, with a giant for a neighbour.",
    "SaturnMoons": "Saturn's moons: rings overhead, and one more world that needs a plan.",
}
# W1-sol: the deeper story. Longer beats for the things that mark a run's arc,
# noted by _note_story_beats() (called every tick from the achievement check):
# each world finished terraforming, the first trade route, and each prestige.
STORY_TERRAFORM_LINES = {
    "Earth": "Earth is finished. The oceans hold, the air is clean, and the pile of iron you started with is now a planet that looks after itself. It only took the whole rest of the system to get here.",
    "Mars": "Mars is green at the edges. The first rain in four billion years is only a drizzle, but the crews stand out in it anyway, and no one mentions the cost.",
    "Moon": "The Moon has an atmosphere now, thin and borrowed, and a horizon that finally looks lived in. From Earth it is a little brighter at night.",
    "Venus": "Venus has cooled. The furnace that scared everyone off is a warm, cloudy world with rivers where nobody expected them, and the patience paid off exactly as slowly as promised.",
    "AsteroidBelt": "The Belt is not a wasteland any more. Its rock is worked, its habitats are lit and its people are numerous enough to have opinions about the rest of the system.",
    "Pluto": "Pluto is warm enough to stand on without a second thought. At the far edge of everything, someone has hung a light in a window.",
    "JupiterMoons": "Jupiter's moons are a system of their own now, with cities under the ice and harbours in the shadow of a giant that does not seem to mind.",
    "SaturnMoons": "Saturn's moons are settled. The rings hang overhead like a promise kept, and the last world on the list has a name and a home in it.",
}
STORY_ROUTE_LINE = "The first trade route runs. A world that only ever produced one thing now has a customer, and the ledger stops being a private matter between you and the ground."
STORY_PRESTIGE_LINE = "You start again, but not from nothing. The routes are gone and the machines are dust, and yet you remember exactly what worked, and the new run begins with that instead of hope."
story_log = []


def story_note(entry_id):
    """Adds an entry id ("arrive:<world>" or "ach:<achievement id>") once."""
    if entry_id in story_log:
        return False
    story_log.append(entry_id)
    del story_log[:-STORY_LOG_MAX]
    return True


def story_line(entry_id):
    """The display text for a log entry id, or None if it is not a known one."""
    kind, _, key = entry_id.partition(":")
    if kind == "arrive":
        return STORY_ARRIVAL_LINES.get(key)
    if kind == "terraform":
        return STORY_TERRAFORM_LINES.get(key)
    if entry_id == "route:first":
        return STORY_ROUTE_LINE
    if kind == "prestige" and key == "1":
        return STORY_PRESTIGE_LINE
    if kind == "rumor":
        entry = RUMOR_BY_ID.get(key)
        return "Ticker: " + entry["text"] if entry else None
    if kind == "ach":
        for entry in ACHIEVEMENTS:
            if entry["id"] == key:
                return f"{entry['label']}: {entry['description']}"
    return None


def story_log_lines():
    """Every log line, oldest first (unknown ids skipped)."""
    return [line for line in (story_line(e) for e in story_log) if line]


def render_story_log():
    latest = document.getElementById("captains-log-latest")
    panel = document.getElementById("captains-log")
    list_el = document.getElementById("captains-log-list")
    lines = story_log_lines()
    own = [line for line in (story_line(e) for e in story_log if not e.startswith("rumor:")) if line]
    latest.hidden = not own  # the rival ticker stays in the log list, never in the headline line
    latest.innerText = f"Captain's log: {own[-1]}" if own else ""
    panel.hidden = not lines
    list_el.innerHTML = ""
    for line in reversed(lines):
        item = document.createElement("li")
        item.innerText = line
        list_el.appendChild(item)


def _mark_visited(planet):
    first_visit = planet not in runstate.visited_bodies
    runstate.visited_bodies.add(planet)
    if first_visit or planet == "Earth":
        story_note(f"arrive:{planet}")
        render_story_log()
