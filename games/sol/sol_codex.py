"""The hidden Codex and the three-goals list."""

import json

from js import document

import sol_runstate as runstate
from sol_observatory import SURVEY_PER_CLUE, _award_survey
from sol_rules import (
    GAS_GIANT_BODIES, PLANETS, PLANET_DISPLAY_NAMES, RESEARCH_NODES, TERRAFORM_MAX, planet_state,
    researched_nodes,
)
from sol_util import _display_toast, _make_button, _make_text


# --- A-19 / A-20: the hidden Codex -----------------------------------------------
# Seven worlds end their Overview note with one odd sentence. Doing what it
# hints at (nothing is timed, random or lost) records a silly Codex curio. The
# Codex section of the Charter stays hidden, and so does its "found n/7" count,
# until the first clue is found; after that every clue that is still open shows
# its odd sentence and a "Show a hint" button that spells out what to do. All
# seven are live conditions on state, except Venus-last, which watches worlds
# finishing terraforming in order (a loaded save counts worlds already done as
# earlier). Collector achievement: Codex Keeper.
WORLD_NOTES = {
    "Moon": "Low gravity, long shadows, patient dust. Thirteen is a number that keeps its promises.",
    "Mars": "Red dust and an old riverbed. Seven kettles will always find Earth.",
    "Venus": "A furnace under a cloud deck. Venus would like to be remembered as the last to finish.",
    "AsteroidBelt": "Rubble that never became a planet. The Belt always counts one short, and likes it.",
    "Pluto": "Cold, far and a little offended. When Pluto goes quiet, it will tell you it is fine.",
    "JupiterMoons": "Floating cities over a storm. A choir with no Recycler hums the loudest.",
    "SaturnMoons": "Ring dust and methane lakes. Round numbers are a kind of respect.",
}
CLUES = [
    {"id": "bakers_dozen", "world": "Moon", "name": "The Baker's Dozen",
     "curio": "Thirteen Auto-Miners on one world. Nobody asked, and it ran fine.",
     "hint": "Own exactly 13 Auto-Miners on a single world.",
     "check": lambda: any(planet_state[p]["generator_count"] == 13 for p in PLANETS)},
    {"id": "seven_kettles", "world": "Mars", "name": "Seven Kettles",
     "curio": "Seven routes lead into Earth. The kettle is always on.",
     "hint": "Have at least 7 trade routes in total that all deliver to Earth.",
     "check": lambda: sum(planet_state[p]["trade_routes"].get("Earth", 0) for p in PLANETS if p != "Earth") >= 7},
    {"id": "last_on_purpose", "world": "Venus", "name": "Last, On Purpose",
     "curio": "Venus finished after everyone else, and has not stopped mentioning it.",
     "hint": "Terraform every other world to 100% first, then finish Venus.",
     "check": lambda: False},  # decided by _check_codex() watching the order worlds finish
    {"id": "off_by_one", "world": "AsteroidBelt", "name": "Off By One",
     "curio": "One Recycler fewer than machines. The Belt counted twice.",
     "hint": "On the Asteroid Belt, own at least 5 Auto-Miners and exactly one fewer Recycler.",
     "check": lambda: planet_state["AsteroidBelt"]["generator_count"] >= 5
     and planet_state["AsteroidBelt"]["recycler_count"] == planet_state["AsteroidBelt"]["generator_count"] - 1},
    {"id": "pluto_is_fine", "world": "Pluto", "name": "Pluto Is Fine",
     "curio": "Ecology at zero and the log says everything is fine. Restore it before it says that again.",
     "hint": "Let Pluto's ecology fall to 0% (it recovers; production just pauses until you rebuild it).",
     "check": lambda: planet_state["Pluto"]["generator_count"] >= 1 and planet_state["Pluto"]["ecology_health"] <= 0},
    {"id": "quiet_choir", "world": "JupiterMoons", "name": "The Quiet Choir",
     "curio": "Three Sky Cities and not one Recycler. They hum anyway.",
     "hint": "Over Jupiter's Moons, build 3 Sky Cities while owning no Recyclers there.",
     "check": lambda: planet_state["JupiterMoons"].get("sky_city_count", 0) >= 3
     and planet_state["JupiterMoons"]["recycler_count"] == 0},
    {"id": "round_number", "world": "SaturnMoons", "name": "Round Number",
     "curio": "Ten thousand Methane in the bank, on purpose.",
     "hint": "Hold 10,000 Methane on Saturn's Moons at once (the Governor spends banked stock, so turn its budget down first).",
     "check": lambda: planet_state["SaturnMoons"]["resource_count"] >= 10000},
]
CLUE_BY_ID = {entry["id"]: entry for entry in CLUES}
codex_found = []  # lifetime, in the order found
_codex_hints = set()  # clues whose hint the player asked for this session


def _check_codex():
    done_now = {p for p in PLANETS if planet_state[p]["terraform_progress"] >= TERRAFORM_MAX}
    others = set(PLANETS) - {"Venus"}
    venus_last = "Venus" in done_now and "Venus" not in runstate._terraform_done_seen and others <= runstate._terraform_done_seen
    runstate._terraform_done_seen = done_now
    for clue in CLUES:
        if clue["id"] in codex_found:
            continue
        if (venus_last if clue["id"] == "last_on_purpose" else clue["check"]()):
            codex_found.append(clue["id"])
            _award_survey(SURVEY_PER_CLUE)
            _display_toast(f"Codex entry found: {clue['name']}")


def _build_codex_section(panel):
    if not codex_found:
        return  # the whole section, and its count, stay hidden until the first clue is found
    panel.appendChild(_make_text("stats-panel-heading", f"Codex: {len(codex_found)} of {len(CLUES)} clues found"))
    for clue in CLUES:
        found = clue["id"] in codex_found
        card = document.createElement("div")
        card.className = "chain-card chain-card--found" if found else "chain-card"
        if found:
            card.appendChild(_make_text("chain-card-name", f"\U0001f4d6 {clue['name']}"))
            card.appendChild(_make_text("chain-card-detail", clue["curio"]))
        else:
            card.appendChild(_make_text("chain-card-name", "Not found yet"))
            note = WORLD_NOTES[clue["world"]]
            card.appendChild(_make_text(
                "chain-card-detail", f"{PLANET_DISPLAY_NAMES.get(clue['world'], clue['world'])} note: \u201c{note.split('. ')[-1]}\u201d"))
            if clue["id"] in _codex_hints:
                card.appendChild(_make_text("chain-card-count", "Hint: " + clue["hint"]))
            else:
                card.appendChild(_make_button("Show a hint", {"data-action": "hint", "data-clue": clue["id"]}, None))
        panel.appendChild(card)


# --- FY-53: "three goals at all times" (shared/goals-panel.js) ---------------
# The game owns the queue; the panel shows the first three that are not done.
# Every goal maps to something SOL already measures, so nothing here is new
# state: it is all derived from planet_state, research and visited_bodies.
def _research_level_progress(tier_index):
    nodes = [n for n in RESEARCH_NODES if n["tier"] == tier_index]
    return sum(1 for n in nodes if n["id"] in researched_nodes), len(nodes)


def _world_available(planet):
    return planet == "Earth" or planet in runstate.unlocked_bodies


def goals_list():
    """The ordered goal queue as plain dicts (id, label, current, target, reward, done)."""
    goals = []
    earth = planet_state["Earth"]
    goals.append({"id": "first_miner", "label": "Build your first Auto-Miner on Earth",
                  "current": min(1, earth["generator_count"]), "target": 1,
                  "reward": "Iron starts mining itself"})
    goals.append({"id": "first_recycler", "label": "Build a Recycler on Earth",
                  "current": min(1, earth["recycler_count"]), "target": 1,
                  "reward": "Slows the ecology decline"})
    done, total = _research_level_progress(0)
    goals.append({"id": "research_near", "label": "Research the Near Bodies level",
                  "current": done, "target": total, "reward": "Opens the Moon and Mars"})
    for planet in ("Mars", "Moon"):
        goals.append({"id": "visit_" + planet.lower(), "label": f"Visit {PLANET_DISPLAY_NAMES.get(planet, planet)}",
                      "current": 1 if planet in runstate.visited_bodies else 0, "target": 1,
                      "reward": "Counts toward Grand Tour"})
    done, total = _research_level_progress(1)
    goals.append({"id": "research_far", "label": "Research the Far Bodies level",
                  "current": done, "target": total, "reward": "Opens five more worlds"})
    goals.append({"id": "first_route", "label": "Build a trade route",
                  "current": min(1, runstate.lifetime_trade_routes_built), "target": 1,
                  "reward": "Ships ecology help to another world"})
    for planet in PLANETS:
        if _world_available(planet):
            name = PLANET_DISPLAY_NAMES.get(planet, planet)
            goals.append({"id": "terraform_" + planet.lower(), "label": f"Terraform {name} to 100%",
                          "current": int(planet_state[planet]["terraform_progress"]), "target": 100,
                          "reward": "Counts toward the whole-system win"})
    for planet in GAS_GIANT_BODIES:
        if _world_available(planet):
            name = PLANET_DISPLAY_NAMES.get(planet, planet)
            goals.append({"id": "sky_" + planet.lower(), "label": f"Build a Sky City over {name}",
                          "current": min(1, planet_state[planet].get("sky_city_count", 0)), "target": 1,
                          "reward": "Boosts that world's output"})
    return goals


def goals_json():
    return json.dumps(goals_list())


def _refresh_goals_panel():
    """Asks the shared panel (when the page has it) to redraw. Cheap; the fake-js
    test environment has no NoyvjGoals so this is a no-op there."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        panel = getattr(js, "NoyvjGoals", None)
        if panel is not None:
            panel.refreshAll()
    except ImportError:
        pass
