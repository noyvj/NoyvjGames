"""Pocket Bazaar -- renown: the slow bar that fills as customers are served and unlocks new goods and customers.

Renown only ever goes up. There is nothing to lose and no deadline: it is a progress bar, shown as a number with the
next unlock named, so the player can always see what comes next.
"""

from goods import FAMILIES

BASE_FAMILIES = ("produce", "textiles", "ceramics")
FAMILY_UNLOCKS = (("spices", 50), ("sweets", 110))
ARCHETYPE_UNLOCKS = (("child", 10), ("tourist", 30), ("crowd", 75))
UNLOCK_NAMES = {"spices": "the Spices crate", "sweets": "the Sweets crate", "child": "children with a coin",
                "tourist": "tourists", "crowd": "rush crowds"}


def gain(served, stars):
    """Renown for a finished day: one per customer served plus a point per star."""
    return served + stars


def families(renown):
    out = list(BASE_FAMILIES)
    for family, need in FAMILY_UNLOCKS:
        if renown >= need:
            out.append(family)
    return [f for f in FAMILIES if f in out]


def archetypes(renown):
    """The extra archetypes (beyond the four every stall starts with) that renown has opened."""
    return {a for a, need in ARCHETYPE_UNLOCKS if renown >= need}


def newly_unlocked(before, after):
    out = []
    for name, need in list(FAMILY_UNLOCKS) + list(ARCHETYPE_UNLOCKS):
        if before < need <= after:
            out.append(name)
    return out


def next_unlock(renown):
    """(name, renown needed) for the nearest unlock still ahead, or None."""
    ahead = [(need, name) for name, need in list(FAMILY_UNLOCKS) + list(ARCHETYPE_UNLOCKS) if need > renown]
    if not ahead:
        return None
    need, name = min(ahead)
    return {"name": UNLOCK_NAMES[name], "need": need}
