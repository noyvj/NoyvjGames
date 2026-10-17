"""The Mission Board with Charter stamps, and Megaprojects."""

import math

from js import document

import sol_runstate as runstate
from sol_codex import _world_available
from sol_observatory import SURVEY_PER_STAMP, _award_survey, relay_bonus
from sol_rules import PLANETS, PLANET_DISPLAY_NAMES, planet_state
from sol_runmods import megaprojects_built
from sol_util import _clean_ids, _display_toast, _overview_planets, _total_trade_routes


# --- A-5 / A-6: the Mission Board and Charter stamps ---------------------------
# Three optional objectives are posted at a time; finishing one stamps the
# Charter (kept for life) and posts the next. Nothing is random: missions are
# offered in catalogue order (worlds you can reach first) and a reroll just moves
# on to the next one. A stamp is a small permanent perk (+1% yield on its world,
# +0.5% everywhere for the world-spanning ones) and shows on the Overview card.
MISSION_SLOTS = 3
CHARTER_MEMBER_STAMPS = 5
STAMP_STAR = "\u2605"
MISSION_REROLL_COST = 100  # of whichever resource pile is biggest right now
_STAMP_BONUS_WORLD = 0.01
_STAMP_BONUS_ALL = 0.005


def _routes(planet):
    return sum(planet_state[planet]["trade_routes"].values())


def _governed_healthy_worlds():
    return sum(
        1 for p in PLANETS
        if p != runstate.current_planet and planet_state[p]["generator_count"] >= 1 and planet_state[p]["ecology_health"] >= 60
    )


MISSIONS = [
    {"id": "earth_crew", "world": "Earth", "target": 8, "label": "Run Earth with 5 Auto-Miners and 3 Recyclers",
     "measure": lambda: min(planet_state["Earth"]["generator_count"], 5) + min(planet_state["Earth"]["recycler_count"], 3)},
    {"id": "earth_hoard", "world": "Earth", "target": 2000, "label": "Bank 2,000 Iron on Earth",
     "measure": lambda: planet_state["Earth"]["resource_count"]},
    {"id": "earth_lean", "world": "Earth", "target": 25,
     "label": "Terraform Earth to 25% with no Auto-Miners at all (Recyclers only)",
     "measure": lambda: planet_state["Earth"]["terraform_progress"] if planet_state["Earth"]["generator_count"] == 0 else 0},
    {"id": "mars_routes", "world": "Mars", "target": 2, "label": "Build 2 trade routes out of Mars",
     "measure": lambda: _routes("Mars")},
    {"id": "mars_calm", "world": "Mars", "target": 6,
     "label": "Run 6 Auto-Miners on Mars with ecology at 90% or more",
     "measure": lambda: planet_state["Mars"]["generator_count"] if planet_state["Mars"]["ecology_health"] >= 90 else 0},
    {"id": "moon_stock", "world": "Moon", "target": 1500, "label": "Bank 1,500 Regolith on the Moon",
     "measure": lambda: planet_state["Moon"]["resource_count"]},
    {"id": "moon_green", "world": "Moon", "target": 50,
     "label": "Terraform the Moon to 50% with 6 Auto-Miners or fewer",
     "measure": lambda: planet_state["Moon"]["terraform_progress"] if planet_state["Moon"]["generator_count"] <= 6 else 0},
    {"id": "venus_sixty", "world": "Venus", "target": 60, "label": "Terraform Venus to 60% with ecology at 50% or more",
     "measure": lambda: planet_state["Venus"]["terraform_progress"] if planet_state["Venus"]["ecology_health"] >= 50 else 0},
    {"id": "belt_bank", "world": "AsteroidBelt", "target": 2500, "label": "Bank 2,500 Platinum in the Asteroid Belt",
     "measure": lambda: planet_state["AsteroidBelt"]["resource_count"]},
    {"id": "belt_routes", "world": "AsteroidBelt", "target": 3, "label": "Build 3 trade routes out of the Asteroid Belt",
     "measure": lambda: _routes("AsteroidBelt")},
    {"id": "pluto_green", "world": "Pluto", "target": 40,
     "label": "Terraform Pluto to 40% with at least 2 Recyclers",
     "measure": lambda: planet_state["Pluto"]["terraform_progress"] if planet_state["Pluto"]["recycler_count"] >= 2 else 0},
    {"id": "jupiter_sky", "world": "JupiterMoons", "target": 2, "label": "Build 2 Sky Cities over Jupiter's Moons",
     "measure": lambda: planet_state["JupiterMoons"].get("sky_city_count", 0)},
    {"id": "saturn_sky", "world": "SaturnMoons", "target": 2, "label": "Build 2 Sky Cities over Saturn's Moons",
     "measure": lambda: planet_state["SaturnMoons"].get("sky_city_count", 0)},
    {"id": "web_of_routes", "world": "all", "target": 6, "label": "Run 6 trade routes in total",
     "measure": lambda: _total_trade_routes()},
    {"id": "governed_well", "world": "all", "target": 3,
     "label": "Have 3 worlds you are not standing on, each with an Auto-Miner and ecology at 60% or more",
     "measure": lambda: _governed_healthy_worlds()},
]
MISSION_BY_ID = {entry["id"]: entry for entry in MISSIONS}
mission_stamps = []  # lifetime, in the order earned
mission_slots = []  # the missions on the board right now

_charter_refs = {}


def stamps_for(world):
    return sum(1 for m_id in mission_stamps if MISSION_BY_ID[m_id]["world"] == world)


def stamp_bonus(planet):
    return _STAMP_BONUS_WORLD * stamps_for(planet) + _STAMP_BONUS_ALL * stamps_for("all") + relay_bonus()


def mission_progress(mission):
    return min(max(0, mission["measure"]()), mission["target"])


def _mission_world_open(mission):
    if mission["world"] == "all":
        return len(_overview_planets()) >= 3
    return _world_available(mission["world"])


def _mission_candidates():
    return [m for m in MISSIONS
            if m["id"] not in mission_stamps and m["id"] not in mission_slots and _mission_world_open(m)]


def _slots_are_default():
    """True while the board is exactly what refilling it from scratch would post (so nothing needs saving)."""
    fresh = [m["id"] for m in MISSIONS if m["id"] not in mission_stamps and _mission_world_open(m)][:MISSION_SLOTS]
    return list(mission_slots) == fresh


def _refill_mission_slots():
    while len(mission_slots) < MISSION_SLOTS:
        candidates = _mission_candidates()
        if not candidates:
            break
        mission_slots.append(candidates[0]["id"])


def _mission_label_world(mission):
    return "the whole system" if mission["world"] == "all" else PLANET_DISPLAY_NAMES.get(mission["world"], mission["world"])


def _check_missions():
    _refill_mission_slots()
    for m_id in list(mission_slots):
        mission = MISSION_BY_ID[m_id]
        if mission["measure"]() >= mission["target"]:
            mission_slots.remove(m_id)
            mission_stamps.append(m_id)
            _award_survey(SURVEY_PER_STAMP)
            _display_toast(f"Charter stamp earned: {mission['label']}")
            _refill_mission_slots()


def reroll_source():
    """(planet, amount) the next reroll would spend, or None when no pile has enough."""
    best = max(_overview_planets(), key=lambda p: planet_state[p]["resource_count"])
    if planet_state[best]["resource_count"] >= MISSION_REROLL_COST:
        return best, MISSION_REROLL_COST
    return None


def reroll_mission(mission_id):
    """Swaps a posted mission for the next one in catalogue order. Returns True when it happened."""
    if mission_id not in mission_slots:
        return False
    source = reroll_source()
    candidates = _mission_candidates()
    if source is None or not candidates:
        return False
    here = MISSIONS.index(MISSION_BY_ID[mission_id])
    later = [m for m in candidates if MISSIONS.index(m) > here]
    chosen = (later or candidates)[0]
    planet_state[source[0]]["resource_count"] -= source[1]
    mission_slots[mission_slots.index(mission_id)] = chosen["id"]
    return True


# --- A-13 / A-14: Megaprojects --------------------------------------------------
# Four late-game works, each fed by resources from several worlds at once. You
# send what a world has banked ("Send what you can" per line), the ring fills by
# whichever worlds have contributed, and a finished work gives a game-warping
# perk for the rest of that run. Building all four (in one run) keeps a secret
# epilogue variant for good. Per run, so each New Game+ can build them again.
MEGAPROJECTS = [
    {"id": "orbital_mirror", "label": "Orbital Mirror", "perk": "Terraforming advances 25% faster everywhere.",
     "needs": [("Earth", 4000), ("Mars", 2500), ("AsteroidBelt", 1500)]},
    {"id": "ring_habitat", "label": "Ring Habitat", "perk": "Sky Cities count double.",
     "needs": [("Moon", 3000), ("Venus", 3000), ("Mars", 3000), ("AsteroidBelt", 2000)]},
    {"id": "dyson_sail", "label": "Dyson Sail", "perk": "Every Auto-Miner produces 20% more.",
     "needs": [("AsteroidBelt", 4000), ("JupiterMoons", 2500), ("Earth", 6000), ("Pluto", 1500)]},
    {"id": "deep_core_tap", "label": "Deep Core Tap", "perk": "Recyclers restore 50% more ecology.",
     "needs": [("SaturnMoons", 3000), ("Pluto", 2500), ("Venus", 3500), ("JupiterMoons", 2500), ("Moon", 2500)]},
]
MEGAPROJECT_BY_ID = {entry["id"]: entry for entry in MEGAPROJECTS}
megaproject_progress = {}  # project id -> {planet: amount sent}


def _mega_need(project_id, planet):
    return dict(MEGAPROJECT_BY_ID[project_id]["needs"]).get(planet, 0)


def megaproject_sent(project_id, planet):
    if project_id in megaprojects_built:
        return _mega_need(project_id, planet)
    return megaproject_progress.get(project_id, {}).get(planet, 0.0)


def megaproject_percent(project_id):
    needs = MEGAPROJECT_BY_ID[project_id]["needs"]
    return 100.0 * sum(min(1.0, megaproject_sent(project_id, p) / amount) for p, amount in needs) / len(needs)


def send_to_megaproject(project_id, planet):
    """Moves what `planet` has banked toward its line of a project. Returns the amount sent."""
    if project_id not in MEGAPROJECT_BY_ID or project_id in megaprojects_built or not _world_available(planet or ""):
        return 0
    need = _mega_need(project_id, planet)
    if need <= 0:
        return 0
    sent = megaproject_progress.setdefault(project_id, {}).get(planet, 0.0)
    amount = min(math.floor(planet_state[planet]["resource_count"] + 1e-9), need - sent)
    if amount <= 0:
        return 0
    planet_state[planet]["resource_count"] -= amount
    megaproject_progress[project_id][planet] = sent + amount
    if all(megaproject_progress[project_id].get(p, 0.0) >= a for p, a in MEGAPROJECT_BY_ID[project_id]["needs"]):
        megaprojects_built.append(project_id)
        _display_toast(f"Megaproject built: {MEGAPROJECT_BY_ID[project_id]['label']}. {MEGAPROJECT_BY_ID[project_id]['perk']}")
        if len(megaprojects_built) == len(MEGAPROJECTS):
            runstate.megaprojects_all_ever = True
    return amount


def _load_megaprojects(data):
    megaproject_progress.clear()
    raw = data.get("megaproject_progress")
    if isinstance(raw, dict):
        for project_id, lines in raw.items():
            if project_id not in MEGAPROJECT_BY_ID or not isinstance(lines, dict):
                continue
            cleaned = {}
            for planet, amount in lines.items():
                need = _mega_need(project_id, planet)
                if need and isinstance(amount, (int, float)) and not isinstance(amount, bool) and 0 < amount < 10 ** 9:
                    cleaned[planet] = min(float(amount), float(need))
            if cleaned:
                megaproject_progress[project_id] = cleaned
    megaprojects_built[:] = [
        pid for pid in _clean_ids(data.get("megaprojects_built"), MEGAPROJECT_BY_ID)
    ]
    runstate.megaprojects_all_ever = data.get("megaprojects_all_ever") is True or len(megaprojects_built) == len(MEGAPROJECTS)


def _ring(percent):
    """A progress ring made from a conic gradient, with the percent as plain text inside."""
    ring = document.createElement("span")
    ring.className = "mega-ring"
    ring.setAttribute("role", "img")
    ring.setAttribute("aria-label", f"{round(percent)} percent built")
    ring.style.background = f"conic-gradient(var(--mega-ring-fill, #6fb3ff) {percent * 3.6}deg, var(--mega-ring-rest, #2a3350) 0)"
    ring.innerText = f"{round(percent)}%"
    return ring
