"""Continuum -- K-5: living ruins (heritage sites).

When the settlement moves on from an era, what it built there does not vanish: it
stays standing at the edge of town as a **heritage site** (a stone circle, a broken
colonnade, a cold chimney). There is one site for every era the settlement has left
behind, so up to seven by the Relay Age. Each site is either:

* **kept** (the default): the old place gives the settlement something to be proud of.
  Every kept site adds `KEEP_BONUS` to the culture bonus, so the fire circles
  (`sim.culture_capacity`) serve a little more of the people. Or
* **demolished**: the player clears it and gets a one-off gift, materials
  (`DEMOLISH_MATERIALS_BASE` plus a little more for later eras) and a small lift to
  land health (`DEMOLISH_LAND`), at a standing cost: culture falls by `DEMOLISH_PENALTY`
  for every site gone, so the settlement serves slightly fewer people socially, which
  reaches the livability score through the same provision it already uses.

Demolishing cannot be undone, so it is always a deliberate, two-step choice in the
UI, never a side effect; keeping is the default and costs nothing. The numbers are
small by design: heritage is a choice with a trade-off, not a lever that decides a run.

No new simulation state. The sites are derived from `campaign.furthest_era`; the only
thing saved is the list of demolished eras in `campaign.ui["heritage"]` (written only
when non-empty, validated on every read, so an older save has none and every site starts
kept). The bonus reaches the season loop through the one research seam (the effects dict).
Sites rest, like every earned advantage, while a challenge run or consulting case is the
active run (there are none, and so no bonus and no demolishing, so those stay comparable).

Pure functions only: no DOM, no storage. `game.py` owns the panel.
"""

import sim

KEY = "heritage"

KEEP_BONUS = 0.06            # added to the culture bonus per kept site
DEMOLISH_PENALTY = 0.05      # taken off the culture bonus per demolished site
DEMOLISH_MATERIALS_BASE = 12.0
DEMOLISH_MATERIALS_PER_ERA = 8.0
DEMOLISH_LAND = 0.03         # land health gained (capped at 1.0)

SITES = {
    "tribal": ("The Founders' Circle", "A ring of standing stones where the first fire was kept."),
    "agrarian": ("The Old Terraces", "Low walls and furrows from the first fields."),
    "classical": ("The Broken Colonnade", "Columns of the first assembly hall, half still upright."),
    "medieval": ("The Watchtower Stump", "The guild tower's stump, where the town bell once hung."),
    "industrial": ("The Cold Chimney", "A single brick chimney, long since out of smoke."),
    "digital": ("The Dark Server Hall", "A slab of dead racks and cable, kept for the stories."),
    "space": ("The First Habitat Ring", "A cracked ring segment, the first home built off the ground."),
}


def _era_ok(era):
    return isinstance(era, str) and era in sim.ERA_ORDER


def demolished(ui):
    """The validated list of demolished era ids (in era order, no repeats, only eras that have a site)."""
    raw = ui.get(KEY) if isinstance(ui, dict) else None
    if not isinstance(raw, dict):
        return []
    items = raw.get("demolished")
    if not isinstance(items, list):
        return []
    seen = {i for i in items if isinstance(i, str) and i in SITES}
    return [era for era in sim.ERA_ORDER if era in seen]


def sites_before(era, ui):
    """The heritage sites that stand behind `era` (the eras before it), with their status."""
    if not _era_ok(era):
        return []
    gone = set(demolished(ui))
    out = []
    for left in sim.ERA_ORDER[: sim.era_index(era)]:
        if left not in SITES:
            continue
        name, blurb = SITES[left]
        out.append({"era": left, "name": name, "blurb": blurb, "kept": left not in gone})
    return out


def counts(ui, furthest_era):
    sites = sites_before(furthest_era, ui)
    kept = sum(1 for s in sites if s["kept"])
    return kept, len(sites) - kept


def culture_delta(ui, furthest_era):
    kept, lost = counts(ui, furthest_era)
    return round(kept * KEEP_BONUS - lost * DEMOLISH_PENALTY, 4)


def apply_effects(effects, ui, furthest_era, resting):
    """The culture bonus kept sites add and demolished ones take away. Returns `effects`
    unchanged when there is nothing to add."""
    if resting:
        return effects
    delta = culture_delta(ui, furthest_era)
    if delta == 0:
        return effects
    out = dict(effects)
    out["culture_bonus"] = max(-0.5, out.get("culture_bonus", 0.0) + delta)
    return out


def demolish_gain(era):
    return DEMOLISH_MATERIALS_BASE + DEMOLISH_MATERIALS_PER_ERA * sim.era_index(era)


def demolish(ui, state, furthest_era, era, resting, revisiting):
    """Clear the heritage site of `era`. Returns (ok, message)."""
    if revisiting:
        return False, "Return to the present before changing a heritage site."
    if resting:
        return False, "Heritage sites rest during a challenge run or consulting case, so those stay comparable."
    standing = {s["era"]: s for s in sites_before(furthest_era, ui)}
    site = standing.get(era) if isinstance(era, str) else None
    if site is None:
        return False, "There is no such heritage site."
    if not site["kept"]:
        return False, f"{site['name']} is already cleared."
    gone = demolished(ui) + [era]
    ui[KEY] = {"demolished": [e for e in sim.ERA_ORDER if e in set(gone)]}
    materials = demolish_gain(era)
    state.resources["materials"] += materials
    state.land_health = min(1.0, state.land_health + DEMOLISH_LAND)
    return True, (
        f"{site['name']} was cleared: {materials:.0f} materials and a little healthier land, "
        f"and culture capacity is {DEMOLISH_PENALTY * 100:.0f}% lower from now on (and no longer "
        f"{KEEP_BONUS * 100:.0f}% higher for keeping it)."
    )


def status_text(site):
    if site["kept"]:
        return f"Kept: adds {KEEP_BONUS * 100:.0f}% to culture capacity."
    return f"Cleared: culture capacity {DEMOLISH_PENALTY * 100:.0f}% lower. It cannot be rebuilt."


def preview_text(era, ui):
    """The Look Back line for one completed era: what it left behind."""
    if era not in SITES:
        return ""
    name, _ = SITES[era]
    gone = era in demolished(ui)
    return f"Heritage: {name}, {'cleared' if gone else 'still standing'}."
