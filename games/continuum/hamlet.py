"""Continuum -- U2: the optional "Hamlet view" (engine half).

U2 (planning/TODO.md, decided by the user): a "Hearth and Hamlet"-style way
to play Continuum on desktop, where the controls live *inside* the scene as
clickable buildings -- one building per "thing" -- instead of a block of
buttons. This is a pilot; Continuum only.

This module is the pure-data half of that view, in the same spirit as
visual.py: no DOM code, no knowledge that Three.js exists, no game logic of
its own. It answers two questions and nothing else:

  1. WHICH buildings does the hamlet show, and WHERE do they stand?
     (`STATIONS`, `stations_for_era()`, `position()`)
  2. What does each one currently say -- count, cost, what a click does,
     whether that click would work right now, and how to describe it to a
     screen reader? (`station_view()`)

What a click actually DOES is never decided here. game.py wires every
station button to the exact same handlers the ordinary Work / Build /
Research panels already use (`_make_assign_handler`, `_make_build_handler`,
`_make_research_handler`, ...), so the hamlet can never drift from the real
rules: there is one implementation of "assign a worker" and this view only
points at it.

A "station" is one clickable building in the hamlet. It is one of:

  - a *workplace* (`role` only): click to put one idle person to work there,
    a small button to take one off -- the Continuum equivalent of "click the
    forester to gather wood";
  - a *structure* (`building` only): click to build one more;
  - a *pair* (both): the natural workplace + building the simulation already
    couples (Fire Circle and its Keepers, Farmland and Farmers, Canals and
    Administrators, ...): click to add a worker, and a separate visible
    button to buy another of the building.

Plus the Town Centre (`kind == "town"`), which stands in for everything that
is not a per-building action: research, civic challenges and moving to the
next era.

Every role and every building the simulation knows appears in exactly one
station (a test asserts it), so nothing playable is lost by hiding the
ordinary panels while the hamlet is on.
"""

import math

import sim

RING_RADIUS = 3.6
SLOT_COUNT = 18  # 16 stations through Space Age; the Relay Age fills slot 16 (slot 17 stays open)

# id, era it appears in, role, building, 3D shape key, ring slot.
#
# Slots are fixed per station (never re-flowed as new ones unlock), so a
# building never moves around as the settlement grows. The Tribal stations
# take the even slots, spread evenly round the ring; later eras fill in the
# odd slots between them, so the ring looks intentional at every stage.
_STATION_ROWS = (
    ("town_centre", "tribal", None, None, "town_centre", 0),
    ("shelter", "tribal", None, "shelter", "shelter", 2),
    ("granary", "tribal", None, "granary", "granary", 4),
    ("fire_circle", "tribal", "keepers", "hearth", "hearth", 6),
    ("knapping", "tribal", "crafters", "toolworks", "toolworks", 8),
    ("foragers", "tribal", "foragers", None, "foragers", 10),
    ("gatherers", "tribal", "gatherers", None, "gatherers", 12),
    ("farm", "agrarian", "farmers", "farmland", "farm", 1),
    ("canal", "classical", "administrators", "canals", "canal", 3),
    ("public_works", "medieval", None, "public_works", "public_works", 5),
    ("guildhall", "medieval", "guildmasters", None, "guildhall", 7),
    ("factory", "industrial", "factory_workers", None, "factory", 9),
    ("sanitation", "industrial", None, "sanitation_works", "sanitation", 11),
    ("planners", "digital", "planners", None, "planners", 13),
    ("transit", "digital", None, "transit_hubs", "transit", 15),
    ("rings", "space", "architects", "habitat_rings", "rings", 14),
    ("relay", "relay", "wayfinders", "relay_stations", "relay", 16),
)

TOWN_ID = "town_centre"
TOWN_EMOJI = "🔔"
TOWN_LABEL = "Town Centre"


def _make_station(row):
    station_id, era, role, building, shape, slot = row
    if station_id == TOWN_ID:
        return {
            "id": station_id, "kind": "town", "era": era, "role": None,
            "building": None, "shape": shape, "slot": slot,
            "label": TOWN_LABEL, "emoji": TOWN_EMOJI,
            "blurb": "Research, civic challenges and the way on to the next era.",
        }
    # A pair is named after its building; a workplace alone after its role.
    if building:
        label, emoji = sim.BUILDING_LABEL[building], sim.BUILDING_EMOJI[building]
    else:
        label, emoji = sim.ROLE_LABEL[role], sim.ROLE_EMOJI[role]
    blurb_parts = []
    if building:
        blurb_parts.append(sim.BUILDING_BLURB[building])
    if role:
        blurb_parts.append(f"{sim.ROLE_LABEL[role]}: {sim.ROLE_BLURB[role]}")
    return {
        "id": station_id, "kind": "station", "era": era, "role": role,
        "building": building, "shape": shape, "slot": slot,
        "label": label, "emoji": emoji, "blurb": " ".join(blurb_parts),
    }


STATIONS = tuple(_make_station(row) for row in _STATION_ROWS)
STATIONS_BY_ID = {station["id"]: station for station in STATIONS}


def stations_for_era(era):
    """Every station a settlement that has reached `era` can use, in the
    stable order of `STATIONS` (the Town Centre first, then Tribal's, then
    each later era's as it unlocks). Also the keyboard tab order."""
    limit = sim.era_index(era)
    return [s for s in STATIONS if sim.era_index(s["era"]) <= limit]


def position(station):
    """Ground-plane (x, z) of a station: a point on the ring, rounded so it
    is stable in a DOM attribute. Angle 0 is straight toward +z."""
    angle = station["slot"] * (2.0 * math.pi / SLOT_COUNT)
    return round(RING_RADIUS * math.sin(angle), 3), round(RING_RADIUS * math.cos(angle), 3)


def flat_percent(x, z):
    """Where a ground point lands on the flat (no-WebGL / 2D view) hamlet,
    as (left%, top%) inside the stage. A plain top-down mapping -- the same
    formula hamlet.js uses, so both halves agree before any 3D projection."""
    reach = RING_RADIUS + 1.4
    return round(50.0 + x / reach * 42.0, 2), round(54.0 + z / reach * 34.0, 2)


def _plural(count, noun):
    return f"{count} {noun}"


def station_view(station, state, effects=None):
    """One plain dict of everything the overlay needs to draw and describe
    `station` right now. A pure function of `(station, state)`.

    `primary` is what clicking the building itself does: "assign" for a
    workplace or pair, "build" for a structure, "open" for the Town Centre.
    `primary_ok` says whether that click would currently do anything, so
    the overlay can dim a blocked building (it stays focusable and says why
    in `aria_label` rather than vanishing from the tab order).
    """
    x, z = position(station)
    view = {
        "id": station["id"], "kind": station["kind"], "label": station["label"],
        "emoji": station["emoji"], "shape": station["shape"], "x": x, "z": z,
        "blurb": station["blurb"],
    }
    if station["kind"] == "town":
        view.update(
            primary="open", primary_ok=True, count=0, count_text="", sub_text="",
            can_unassign=False, has_build_button=False, can_build=False, cost=None,
            workers=None, built=None,
            aria_label=f"{TOWN_LABEL}. Opens research, civic challenges and era advance.",
            title=f"{TOWN_LABEL} -- {station['blurb']}",
        )
        return view

    role, building = station["role"], station["building"]
    idle = state.idle_workers()
    workers = state.allocation[role] if role else None
    built = state.buildings[building] if building else None
    cost = sim.BUILDING_COST[building] if building else None
    can_build = bool(building) and state.can_build(building)
    can_assign = bool(role) and idle > 0
    role_name = sim.ROLE_LABEL[role].lower() if role else ""
    label = station["label"]

    if role:
        primary, primary_ok = "assign", can_assign
        count = workers
        count_text = f"×{built}" if building else f"👤{workers}"
    else:
        primary, primary_ok = "build", can_build
        count = built
        count_text = f"×{built}"

    # The one always-visible caption: a structure shows what one more costs;
    # a pair shows its workers (its build cost is on its own button).
    if role and building:
        sub_text = f"👤{workers}"
    elif building:
        sub_text = f"＋{cost:.0f}"
    else:
        sub_text = ""

    facts = []
    if building:
        facts.append(f"{built} built")
    if role:
        facts.append(f"{_plural(workers, role_name)} working")
    if primary == "assign":
        action = f"Activate to put one idle person to work as {role_name}."
        if not can_assign:
            action = f"No one is idle to assign as {role_name}."
    else:
        action = f"Activate to build one more for {cost:.0f} materials."
        if not can_build:
            missing = max(0.0, cost - state.resources["materials"])
            action = f"Build one more costs {cost:.0f} materials; {missing:.0f} more needed."
    aria_label = f"{label}. {', '.join(facts)}. {action}"
    if role and building:
        aria_label += f" A separate button builds another for {cost:.0f} materials."

    view.update(
        primary=primary, primary_ok=primary_ok, count=count, count_text=count_text,
        sub_text=sub_text, can_unassign=bool(role) and workers > 0,
        has_build_button=bool(role and building), can_build=can_build, cost=cost,
        workers=workers, built=built, aria_label=aria_label,
        title=f"{label} -- {station['blurb']}",
    )
    return view


def researchable_nodes(tree):
    """Research nodes the Town Centre can offer to study right now: available
    (prerequisites and tier met) and not yet known, cheapest first."""
    nodes = [
        node for node in tree.visible_nodes()
        if not tree.is_researched(node.node_id) and tree.is_available(node.node_id)
    ]
    return sorted(nodes, key=lambda node: (node.cost, node.node_id))


def locked_count(tree):
    """How many visible nodes are still locked -- for a one-line hint."""
    return sum(
        1 for node in tree.visible_nodes()
        if not tree.is_researched(node.node_id) and not tree.is_available(node.node_id)
    )
