"""Lighthouse -- three standing goals, always on screen: the next reputation title, the nearest upgrade, and the
next thing to explore. They have no order and no deadline; each shows progress as "a of b" and a bar, and is
replaced by the next one the moment it is done. Pure reading of the keep."""

from data import NIGHTS_PER_YEAR, PARTS, REP_TITLES, UPGRADES
import clock


def _rep_goal(keep):
    for threshold, name in REP_TITLES:
        if keep.reputation < threshold:
            return {"id": "rep", "label": "Become %s to the harbour" % name, "have": keep.reputation, "need": threshold}
    return None


def _upgrade_goal(keep):
    left = [u for u in UPGRADES if u["id"] not in keep.upgrades]
    if not left:
        return None
    nearest = min(left, key=lambda u: (max(0, u["cost"] - keep.salvage), u["cost"]))
    return {"id": "upgrade", "label": "Save salvage for the %s" % nearest["name"].lower(), "have": min(keep.salvage, nearest["cost"]), "need": nearest["cost"]}


def _explore_goal(keep):
    """The first of these that is not done yet. Every one is something a player can simply go and do."""
    c = keep.meta["counters"]
    if keep.mode == "year":
        done = clock.year_night(keep.night) - (1 if keep.phase in ("evening", "night") else 0)
        if done < NIGHTS_PER_YEAR and keep.meta["years"] < 1:
            return {"id": "year", "label": "Keep the light through the first year", "have": max(0, done), "need": NIGHTS_PER_YEAR}
    ladder = (
        ("quiet_nights", 1, "Have a night with no trouble at all"),
        ("tidy_days", 1, "Mend every part of the station in a single day"),
        ("fog_clears", 1, "Bring every ship through a long fog"),
        ("storm_wardens", 1, "Come through a storm with every part above half"),
        ("best_wound_streak", 7, "Keep the clockwork turning seven nights running"),
        ("frugal_seasons", 1, "Finish a season with the oil never below 20"),
        ("empty_nights", 1, "Find a night with nothing in the log"),
    )
    for key, need, label in ladder:
        if c.get(key, 0) < need:
            return {"id": key, "label": label, "have": min(c.get(key, 0), need), "need": need}
    if keep.mode != "endless":
        return {"id": "endless", "label": "Keep the light as a keeper for life", "have": 0, "need": 1}
    return {"id": "mend", "label": "Bring every part of the station to 100", "have": sum(1 for p in PARTS if keep.structure[p] >= 100), "need": len(PARTS)}


def goals(keep):
    out = [g for g in (_rep_goal(keep), _upgrade_goal(keep), _explore_goal(keep)) if g]
    for g in out:
        g["done"] = g["have"] >= g["need"]
    return out
