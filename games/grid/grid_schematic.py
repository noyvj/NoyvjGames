"""The single-line schematic (C-11): rows, flow widths, caption and SVG.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import GENERATION_TYPES, PLANT_LABEL


# ---- C-11 single-line schematic ---------------------------------------------------------------------------------------
# A power-engineer's "single line" picture of the grid as it stands: each type of plant you have is a box on the left, a line
# from it to a vertical bus whose thickness is how much it delivers, the bus feeds one demand block on the right (with
# whether it is met) and a battery tank beside it shows how full storage is. The picture is built from plain attributes
# (no style sheet), so the "Save schematic image" button can turn it into a PNG that stands on its own; on the page a few
# rounds of flowing dashes play after each change (CSS, off under Reduce motion). A line of words repeats everything.
SCHEMATIC_WIDTH = 300
SCHEMATIC_HEIGHT = 150
SCHEMATIC_COLOR = {
    "coal": "#a3a8bb", "gas": "#e0a24c", "nuclear": "#d6e04e", "solar": "#ffd95e", "wind": "#cfe0ff", "hydro": "#4fa8dd",
}
SCHEMATIC_MIN_FLOW = 1.5
SCHEMATIC_MAX_FLOW = 10.5


def schematic_rows():
    """(plant type, units, delivered) for every generation type standing, in the usual order. 'Delivered' is the type's share
    of what the grid can actually sell (capacity up to demand), the same split the fleet table uses for revenue."""
    paid = min(runstate.state.total_capacity(), runstate.state.demand)
    return [
        (t, runstate.state.plant_counts[t], runstate.state.capacity_share(t) * paid)
        for t in GENERATION_TYPES if runstate.state.plant_counts[t] > 0
    ]


def schematic_flow_width(delivered):
    demand = max(runstate.state.demand, 1.0)
    return min(SCHEMATIC_MAX_FLOW, SCHEMATIC_MIN_FLOW + (SCHEMATIC_MAX_FLOW - SCHEMATIC_MIN_FLOW) * delivered / demand)


def schematic_caption():
    rows = schematic_rows()
    capacity = runstate.state.total_capacity()
    if not rows:
        parts = ["Nothing is generating yet, so no power reaches the demand block."]
    else:
        gens = ", ".join(f"{PLANT_LABEL[t]} {n} unit{'s' if n != 1 else ''} delivering {d:.0f}" for t, n, d in rows)
        parts = [f"{gens}, all feeding one bus."]
    if capacity >= runstate.state.demand:
        parts.append(f"Demand {runstate.state.demand:.0f} is fully supplied.")
    else:
        parts.append(f"Demand {runstate.state.demand:.0f} is short by {runstate.state.demand - capacity:.0f} ({capacity / max(runstate.state.demand, 1) * 100:.0f}% supplied).")
    if runstate.state.plant_counts["battery"] > 0:
        parts.append(f"Battery holds {runstate.state.stored_energy:.0f} of {runstate.state.storage_cap():.0f}.")
    else:
        parts.append("No battery storage yet.")
    return " ".join(parts)


def schematic_svg():
    w, h = SCHEMATIC_WIDTH, SCHEMATIC_HEIGHT
    rows = schematic_rows()
    capacity = runstate.state.total_capacity()
    bus_x, demand_x = 128, 196
    out = [f'<rect x="0" y="0" width="{w}" height="{h}" rx="6" fill="#14182b" />']
    out.append('<text x="8" y="11" font-size="8" fill="#9aa3d6" font-family="sans-serif">Generation</text>')
    out.append(f'<text x="{demand_x}" y="11" font-size="8" fill="#9aa3d6" font-family="sans-serif">Demand</text>')
    ys = []
    for index, (plant_type, units, delivered) in enumerate(rows):
        y = 24 + index * 20
        ys.append(y)
        color = SCHEMATIC_COLOR[plant_type]
        out.append(f'<rect x="8" y="{y - 8}" width="74" height="16" rx="3" fill="#1f2547" stroke="{color}" stroke-width="1.2" />')
        out.append(
            f'<text x="12" y="{y + 3}" font-size="9" fill="#e8ecff" font-family="sans-serif">{PLANT_LABEL[plant_type]} x{units}</text>'
        )
        out.append(
            f'<line x1="82" y1="{y}" x2="{bus_x}" y2="{y}" stroke="{color}" stroke-width="{schematic_flow_width(delivered):.1f}" '
            f'stroke-dasharray="6 4" class="sch-flow" />'
        )
    mid_y = 60
    if ys:
        out.append(f'<line x1="{bus_x}" y1="{ys[0]}" x2="{bus_x}" y2="{ys[-1]}" stroke="#e8ecff" stroke-width="3" stroke-linecap="round" />')
        mid_y = (ys[0] + ys[-1]) / 2
        total = min(capacity, runstate.state.demand)
        out.append(
            f'<line x1="{bus_x}" y1="{mid_y:.0f}" x2="{demand_x}" y2="{mid_y:.0f}" stroke="#e8ecff" '
            f'stroke-width="{schematic_flow_width(total):.1f}" stroke-dasharray="6 4" class="sch-flow" />'
        )
    else:
        out.append(f'<line x1="{bus_x}" y1="{mid_y}" x2="{demand_x}" y2="{mid_y}" stroke="#5d6490" stroke-width="1.5" stroke-dasharray="2 4" />')
    met = capacity >= runstate.state.demand
    block_stroke = "#7fd6a3" if met else "#ff9f80"
    out.append(f'<rect x="{demand_x}" y="14" width="96" height="58" rx="4" fill="#1f2547" stroke="{block_stroke}" stroke-width="1.5"' + ("" if met else ' stroke-dasharray="4 2"') + " />")
    out.append(f'<text x="{demand_x + 6}" y="30" font-size="9" fill="#e8ecff" font-family="sans-serif">Demand {runstate.state.demand:.0f}</text>')
    status = "MET" if met else f"SHORT by {runstate.state.demand - capacity:.0f}"
    out.append(f'<text x="{demand_x + 6}" y="44" font-size="9" font-weight="bold" fill="{block_stroke}" font-family="sans-serif">{status}</text>')
    out.append(
        f'<text x="{demand_x + 6}" y="58" font-size="8" fill="#9aa3d6" font-family="sans-serif">Round {runstate.state.round_number} | '
        f'{min(100, capacity / max(runstate.state.demand, 1) * 100):.0f}% supplied</text>'
    )
    out.append(f'<text x="{demand_x}" y="88" font-size="8" fill="#9aa3d6" font-family="sans-serif">Storage</text>')
    out.append(f'<rect x="{demand_x}" y="92" width="30" height="46" rx="3" fill="none" stroke="#e8ecff" stroke-width="1.2" />')
    cap = runstate.state.storage_cap()
    if runstate.state.plant_counts["battery"] > 0 and cap > 0:
        fill = max(0.0, min(1.0, runstate.state.stored_energy / cap))
        out.append(f'<rect x="{demand_x + 1.5}" y="{93.5 + 43 * (1 - fill):.1f}" width="27" height="{43 * fill:.1f}" fill="#4fa8dd" />')
        label = f"{runstate.state.stored_energy:.0f} of {cap:.0f}"
    else:
        label = "none built"
    out.append(f'<text x="{demand_x + 36}" y="118" font-size="8" fill="#e8ecff" font-family="sans-serif">{label}</text>')
    out.append(f'<text x="8" y="{h - 6}" font-size="7" fill="#6f78a8" font-family="sans-serif">Grid single line: line thickness = power delivered</text>')
    caption = schematic_caption()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w * 2}" height="{h * 2}" class="schematic-svg" '
        f'role="img" aria-label="{caption}"><title>{caption}</title>{"".join(out)}</svg>'
    )


def render_schematic():
    document.getElementById("schematic-graphic").innerHTML = schematic_svg()
    document.getElementById("schematic-caption").innerText = schematic_caption()
