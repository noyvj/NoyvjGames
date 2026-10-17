"""render_map(): draws the whole trade map on its canvas."""

import math

from js import document

import trade_runstate as runstate
from trade_blackout import blackout_has
from trade_colony import active_colony_ids, colony_states
from trade_hub import HUB_RING_WIDTH, hub_map_tooltip
from trade_mapdraw import (
    AUTOMATED_SHIP_COLOR, CANVAS_HEIGHT, CANVAS_WIDTH, EDGE_COLOR, FLEET_PRIORITY_TARGET_COLOR, LABEL_COLOR,
    MANUAL_SHIP_COLOR, NODE_COLOR, NODE_POSITIONS, NODE_RADIUS, SHIP_DOT_RADIUS, colony_map_label,
    draw_dock_pulses, draw_temperament_glyph, route_edges, ship_map_position,
)
from trade_research import most_urgent_colony
from trade_rules import ALL_COLONIES
from trade_ships import ships


def render_map():
    canvas = document.getElementById("map-canvas")
    ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
    if not blackout_has("chart"):  # J-29: Blackout, the star chart is dark
        canvas.title = "Blackout: the map is dark. Buy the star chart or research Galaxy Expansion to light it."
        ctx.fillStyle = LABEL_COLOR
        ctx.font = "14px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText("Blackout: the star chart is dark", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 10)
        ctx.fillText("(colonies and needs are still listed below)", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 12)
        return
    # J6 — hover text explaining what the pink target ring points at.
    if runstate.fleet_priority_enabled and colony_states:
        canvas.title = (
            f"Pink ring: Fleet Priority's current target, {ALL_COLONIES[most_urgent_colony()]['name']} "
            "(the colony with the lowest need satisfaction). Idle automated ships reposition "
            "toward whichever producer feeds it."
        )
    else:
        canvas.title = "Trade routes map. Turn on Fleet Priority to see its target ring."
    canvas.title += hub_map_tooltip()  # J-22

    ctx.strokeStyle = EDGE_COLOR
    ctx.lineWidth = 2
    for from_id, to_id in route_edges():
        x1, y1 = NODE_POSITIONS[from_id]
        x2, y2 = NODE_POSITIONS[to_id]
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()

    # Milestone 13: only draw nodes the player can actually reach right
    # now -- a locked Kepler Cluster stays entirely off the map.
    for colony_id in active_colony_ids():
        x, y = NODE_POSITIONS[colony_id]
        ctx.fillStyle = NODE_COLOR
        ctx.beginPath()
        ctx.arc(x, y, NODE_RADIUS, 0, 2 * math.pi)
        ctx.fill()

        ctx.fillStyle = LABEL_COLOR
        ctx.font = "11px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(colony_map_label(colony_id), x, y)
        if colony_id in colony_states:
            draw_temperament_glyph(ctx, colony_id, x + NODE_RADIUS * 0.8, y - NODE_RADIUS * 0.8)
        if colony_id == runstate.hub_colony:  # J-22: a thick ring and the word HUB (shape and text, not colour only)
            ctx.strokeStyle = LABEL_COLOR
            ctx.lineWidth = HUB_RING_WIDTH
            ctx.beginPath()
            ctx.arc(x, y, NODE_RADIUS + 3, 0, 2 * math.pi)
            ctx.stroke()
            ctx.fillStyle = LABEL_COLOR
            ctx.fillText("HUB", x, y + NODE_RADIUS + 13)

    # J16 — Fleet Priority's current target, made visible rather than
    # left implicit: a ring around whichever colony most_urgent_colony()
    # would currently send an idle automated ship toward.
    if runstate.fleet_priority_enabled and colony_states:
        target = most_urgent_colony()
        if target in NODE_POSITIONS:
            tx, ty = NODE_POSITIONS[target]
            ctx.strokeStyle = FLEET_PRIORITY_TARGET_COLOR
            ctx.lineWidth = 3
            ctx.beginPath()
            ctx.arc(tx, ty, NODE_RADIUS + 6, 0, 2 * math.pi)
            ctx.stroke()

    draw_dock_pulses(ctx)

    for ship in ships.values():
        if not ship.purchased or ship.on_expedition:
            continue
        x, y = ship_map_position(ship)
        ctx.fillStyle = AUTOMATED_SHIP_COLOR if ship.automated else MANUAL_SHIP_COLOR
        if ship.automated:
            # J18 — colorblind-safe differentiation: a diamond, not just
            # a different hue, so automated-vs-manual doesn't rely on
            # color perception at all.
            ctx.beginPath()
            ctx.moveTo(x, y - SHIP_DOT_RADIUS)
            ctx.lineTo(x + SHIP_DOT_RADIUS, y)
            ctx.lineTo(x, y + SHIP_DOT_RADIUS)
            ctx.lineTo(x - SHIP_DOT_RADIUS, y)
            ctx.closePath()
            ctx.fill()
        else:
            ctx.beginPath()
            ctx.arc(x, y, SHIP_DOT_RADIUS, 0, 2 * math.pi)
            ctx.fill()
