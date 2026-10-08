"""Lighthouse -- who is on the water. A pure function of (seed, night): it only RENAMES and LABELS ships the sim
already generated (never adds, removes or retimes one), so the sim plays out identically with the story layer on or
off. Which letters a sailor sends is decided later, in story.py, by how often their ship got safely by."""

from lore import SAILORS
from rng import unit

MAX_PER_NIGHT = 2


def assign(seed, night, ships):
    """Label ships in place with `who` (a sailor id) and, for sailors who own a boat, its name."""
    taken = 0
    for sid, s in SAILORS.items():
        kind = s["kind"]
        if not kind or night < s["min_night"]:
            continue
        if kind != "mail" and taken >= MAX_PER_NIGHT:
            continue
        pool = [sh for sh in ships if sh["kind"] == kind and not sh.get("who")]
        if not pool or unit(seed, "cast", sid, night) >= s["chance"]:
            continue
        ship = pool[0]
        ship["who"] = sid
        if s["ship"]:
            ship["name"] = s["ship"]
        if kind != "mail":
            taken += 1
    return ships
