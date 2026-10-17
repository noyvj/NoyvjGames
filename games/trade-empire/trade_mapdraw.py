"""The trade map's fixed parts: node positions, colours, route edges, ship positions, dock pulses and temperament glyphs (render_map itself is in trade_mapview)."""

import math

from trade_colony import active_colony_ids, colony_needing, colony_states
from trade_rules import ALL_COLONIES, TEMPERAMENTS
from trade_uikit import _effects_on, _reduced_motion_on


# Milestone 7 — 2D map v1: colonies as nodes, routes as lines. Drawn
# directly from Python via Pyodide's `js` module (canvas 2D context
# methods are just JS method calls, so no separate JS glue file is
# needed here despite the canvas requirement). Static layout and static
# routes for now — no moving ships until Milestone 11.
CANVAS_WIDTH = 620
# J1 — the Umbral Deep gets its own band along the bottom, so the canvas
# grew taller rather than wider (it is displayed at a fixed max width, so
# widening it again would have shrunk every existing node further).
CANVAS_HEIGHT = 450
NODE_RADIUS = 22
NODE_POSITIONS = {
    "aurum": (150, 36),
    "verdant": (262, 118),
    "ferrum": (218, 252),
    "cryo": (82, 252),
    "helion": (38, 118),
    # Milestone 13 — the Kepler Cluster sits in its own space on the
    # right half of the (now wider) canvas, visually distinct from the
    # home system's pentagon rather than crowded into it. Positions kept
    # exactly as Milestone 13 placed them (not re-centered for J13's
    # further widening below) so an in-flight ship's saved interpolation
    # coordinates stay valid.
    "kepler_a": (390, 50),
    "kepler_b": (430, 190),
    "kepler_c": (350, 230),
    # J13 — the Rift Colonies get their own space again, further right
    # still, on the canvas' newly-widened third of the width.
    "rift_a": (560, 50),
    "rift_b": (595, 190),
    "rift_c": (520, 250),
    # J1 — the Umbral Deep: its own band below every other system.
    "deep_a": (250, 350),
    "deep_b": (370, 415),
    "deep_c": (490, 350),
}
NODE_COLOR = "#3a5a9c"
EDGE_COLOR = "#3a3f5c"
LABEL_COLOR = "#e8e9f0"

# Bug fix, found during the code-quality audit: render_map() used to
# label every node with name.split()[0]. That's unique for the home
# system (Aurum/Verdant/Ferrum/Cryo/Helion all have distinct first
# words), but all three Kepler Cluster colonies share the literal
# prefix "Kepler" -- naively reusing the same rule rendered all three
# map nodes with the identical "Kepler" label, making them visually
# indistinguishable despite sitting at three different positions.
# Kepler colonies get an explicit short label instead; everything else
# keeps the original first-word behavior unchanged.
MAP_LABEL_OVERRIDE = {
    "kepler_a": "Kep. Alpha",
    "kepler_b": "Kep. Beta",
    "kepler_c": "Kep. Gamma",
    # J13 — same collision as Kepler's: all three Rift colonies share the
    # literal first word "Rift".
    "rift_a": "Rift Alpha",
    "rift_b": "Rift Beta",
    "rift_c": "Rift Gamma",
}


def colony_map_label(colony_id):
    return MAP_LABEL_OVERRIDE.get(colony_id, ALL_COLONIES[colony_id]["name"].split()[0])


def route_edges():
    """One directed edge per *reachable* colony, to whichever colony
    needs its produced good -- the same relationship colony_needing()
    already encodes, just read as a full list for drawing. Scoped to
    active_colony_ids() so a locked Kepler Cluster never contributes
    edges pointing at nodes the map isn't drawing yet."""
    edges = []
    for colony_id in active_colony_ids():
        destination = colony_needing(ALL_COLONIES[colony_id]["produces"])
        if destination:
            edges.append((colony_id, destination))
    return edges


# Milestone 11 — ships on the map: automated routes (and manual ones,
# so the map stays useful during manual play too) render as moving
# dots along the map's lines, interpolated between origin and
# destination using the trip's own fixed tick count at departure time
# (transit_total_ticks) rather than the current travel_ticks(), so a
# mid-flight ship's position stays consistent even if Fast Ships
# research changes the travel time for future departures.
SHIP_DOT_RADIUS = 5
AUTOMATED_SHIP_COLOR = "#e0c34c"
MANUAL_SHIP_COLOR = "#e8e9f0"
# J16 — a color distinct from every node/edge/ship hue already in use.
FLEET_PRIORITY_TARGET_COLOR = "#ff6ad0"


def ship_map_position(ship):
    if ship.location is not None:
        return NODE_POSITIONS[ship.location]
    origin_x, origin_y = NODE_POSITIONS[ship.origin]
    dest_x, dest_y = NODE_POSITIONS[ship.destination]
    if ship.transit_total_ticks <= 0:
        progress = 1.0
    else:
        elapsed = ship.transit_total_ticks - ship.transit_ticks_remaining
        progress = max(0.0, min(1.0, elapsed / ship.transit_total_ticks))
    return (
        origin_x + (dest_x - origin_x) * progress,
        origin_y + (dest_y - origin_y) * progress,
    )


# J10 -- a brief docking/undocking pulse on the map. Undocking is a ring
# that grows outward from the colony a ship just left; docking is a ring
# that closes in on the colony a ship just reached. Direction and line
# weight carry the meaning (not colour), each pulse lasts DOCK_PULSE_TICKS
# ticks, and none are drawn while the player has reduced motion on. Purely
# a view effect: nothing is saved.
DOCK_PULSE_TICKS = 3
dock_pulses = []  # [colony_id, "dock" | "undock", age_in_ticks]


def add_dock_pulse(colony_id, kind):
    if colony_id in NODE_POSITIONS:
        dock_pulses.append([colony_id, kind, 0])


def age_dock_pulses():
    for pulse in dock_pulses:
        pulse[2] += 1
    dock_pulses[:] = [p for p in dock_pulses if p[2] < DOCK_PULSE_TICKS]


def dock_pulse_radius(kind, age):
    step = age / DOCK_PULSE_TICKS
    if kind == "undock":
        return NODE_RADIUS + 4 + step * 18
    return NODE_RADIUS + 4 + (1 - step) * 18


def draw_dock_pulses(ctx):
    if _reduced_motion_on() or not _effects_on():
        return
    for colony_id, kind, age in dock_pulses:
        if colony_id not in active_colony_ids():
            continue
        x, y = NODE_POSITIONS[colony_id]
        ctx.strokeStyle = LABEL_COLOR
        ctx.lineWidth = 3 if kind == "dock" else 1.5
        ctx.beginPath()
        ctx.arc(x, y, dock_pulse_radius(kind, age), 0, 2 * math.pi)
        ctx.stroke()


TEMPERAMENT_GLYPH_COLOR = "#f4e9b8"
TEMPERAMENT_GLYPH_RADIUS = 6


def temperament_glyph_points(glyph, cx, cy, r=TEMPERAMENT_GLYPH_RADIUS):
    """J-26 -- polygon points for a colony mood glyph: a circle (drawn as a
    12-sided shape, so the map's own arcs stay one per node), a triangle or a
    square. The shape, not its colour, carries the meaning."""
    if glyph == "triangle":
        return [(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    if glyph == "square":
        return [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    return [(cx + r * math.cos(i * math.pi / 6), cy + r * math.sin(i * math.pi / 6)) for i in range(12)]


def draw_temperament_glyph(ctx, colony_id, cx, cy):
    glyph = TEMPERAMENTS[colony_states[colony_id].temperament()]["glyph"]
    points = temperament_glyph_points(glyph, cx, cy)
    ctx.fillStyle = TEMPERAMENT_GLYPH_COLOR
    ctx.beginPath()
    ctx.moveTo(*points[0])
    for px, py in points[1:]:
        ctx.lineTo(px, py)
    ctx.closePath()
    ctx.fill()
