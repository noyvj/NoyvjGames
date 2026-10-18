"""Opt-in rich SVG trade-network and supply-chain maps (H25b/H29b) and their toggles."""

import html
import math

from js import document

import loop_runstate as runstate
from loop_rules import (
    CIRCULARITY_INVESTMENTS, EXPORT_PRICE_PER_UNIT, IMPORT_SUPPLY_PER_UNIT, OVERSEAS_IMPORT_SUPPLY_PER_UNIT,
    OVERSEAS_TRADE_COST, REGIONAL_IMPORT_SUPPLY_PER_UNIT, REGIONAL_TRADE_COST, TRADE_LINK_COST,
)


# ===========================================================================
# H25b/H29b: richer, opt-in SVG versions of the trade network (H25a) and the
# circular supply chain map (H29a). Every number is read from the live
# ChainState (nothing invented); the simple text versions above stay the
# default and keep working everywhere. The SVG is built here as plain
# strings (pure functions of state, so directly testable); the wide-screen
# breakout, tooltips, animation and the narrow-screen fallback note are CSS
# and rich-maps.js. Browser preference only (never part of a save code).
# ===========================================================================
RICH_MIN_WIDTH_PX = 900  # mirrors the @media breakpoint in style.css


def _esc(value):
    return html.escape(str(value), quote=True)


def _fmt(units):
    """Units per cycle: whole numbers plain, fractional ones to 1 dp."""
    return f"{units:.0f}" if abs(units - round(units)) < 0.05 else f"{units:.1f}"


def _flow_width(units, scale):
    """Stroke width (viewBox units) for a flow; 0 means no flow at all.
    Proportional to units over the largest flow in the same map."""
    if units <= 0:
        return 0.0
    return 3.0 + 25.0 * min(1.0, units / max(scale, 1.0))


def _node_radius(units, scale, base=22.0, extra=18.0):
    """Node radius, growing with the square root of its share of the
    largest flow (so area, not width, tracks the amount)."""
    if units <= 0:
        return base - 4.0
    return base + extra * math.sqrt(min(1.0, units / max(scale, 1.0)))


def _cubic(p0, c1, c2, p3, t):
    u = 1.0 - t
    x = u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1]
    dx = 3 * u * u * (c1[0] - p0[0]) + 6 * u * t * (c2[0] - c1[0]) + 3 * t * t * (p3[0] - c2[0])
    dy = 3 * u * u * (c1[1] - p0[1]) + 6 * u * t * (c2[1] - c1[1]) + 3 * t * t * (p3[1] - c2[1])
    return (x, y), (dx, dy)


def _edge_point(centre, radius, toward):
    """The point on a node's circle facing `toward`."""
    dx, dy = toward[0] - centre[0], toward[1] - centre[1]
    length = math.hypot(dx, dy) or 1.0
    return (centre[0] + dx / length * radius, centre[1] + dy / length * radius)


def _straight(a, ra, b, rb):
    """Endpoints of a straight flow between two nodes' circle edges."""
    p0 = _edge_point(a, ra, b)
    p3 = _edge_point(b, rb, a)
    c1 = (p0[0] + (p3[0] - p0[0]) / 3.0, p0[1] + (p3[1] - p0[1]) / 3.0)
    c2 = (p0[0] + 2.0 * (p3[0] - p0[0]) / 3.0, p0[1] + 2.0 * (p3[1] - p0[1]) / 3.0)
    return p0, c1, c2, p3


def _svg_flow(kind, units, scale, geometry, tip):
    """One flow: a thickness-scaled band, an animated direction overlay, an
    arrowhead (so direction survives reduced motion), and a focusable,
    labelled hover target carrying the real numbers."""
    p0, c1, c2, p3 = geometry
    d = f"M{p0[0]:.1f},{p0[1]:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}"
    width = _flow_width(units, scale)
    idle = width <= 0
    classes = f"rich-hit rich-flow rf--{kind}" + (" rf--idle" if idle else "")
    parts = [
        f'<g class="{classes}" tabindex="0" role="img" aria-label="{_esc(tip)}" data-tip="{_esc(tip)}">',
        f'<path class="rf-hit" d="{d}" />',
        f'<path class="rf-base" d="{d}" stroke-width="{max(width, 2.0):.1f}" />',
    ]
    if not idle:
        parts.append(f'<path class="rf-dash" d="{d}" />')
        (mx, my), (tx, ty) = _cubic(p0, c1, c2, p3, 0.55)
        length = math.hypot(tx, ty) or 1.0
        ux, uy = tx / length, ty / length
        size = 7.0 + width * 0.45
        tip_pt = (mx + ux * size, my + uy * size)
        base_l = (mx - ux * size * 0.6 - uy * size * 0.75, my - uy * size * 0.6 + ux * size * 0.75)
        base_r = (mx - ux * size * 0.6 + uy * size * 0.75, my - uy * size * 0.6 - ux * size * 0.75)
        parts.append(
            f'<polygon class="rf-arrow" points="{tip_pt[0]:.1f},{tip_pt[1]:.1f} '
            f'{base_l[0]:.1f},{base_l[1]:.1f} {base_r[0]:.1f},{base_r[1]:.1f}" />'
        )
    parts.append("</g>")
    return "".join(parts)


def _svg_node(kind, centre, radius, icon, label, value, tip, label_at="below"):
    x, y = centre
    if label_at == "above":
        lx, ly, anchor = x, y - radius - 24, "middle"
    elif label_at == "right":
        lx, ly, anchor = x + radius + 10, y - 2, "start"
    elif label_at == "corner":
        lx, ly, anchor = x + radius * 0.72 + 8, y + radius * 0.9 + 10, "start"
    else:
        lx, ly, anchor = x, y + radius + 16, "middle"
    return (
        f'<g class="rich-hit rich-node rn--{kind}" tabindex="0" role="img" '
        f'aria-label="{_esc(tip)}" data-tip="{_esc(tip)}">'
        f'<circle class="rn-shape" cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" />'
        f'<text class="rn-icon" x="{x:.1f}" y="{y + 7:.1f}" text-anchor="middle">{icon}</text>'
        f'<text class="rn-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{_esc(label)}</text>'
        f'<text class="rn-value" x="{lx:.1f}" y="{ly + 16:.1f}" text-anchor="{anchor}">{_esc(value)}</text>'
        f"</g>"
    )


def _legend_html(items, note):
    entries = "".join(
        f'<li><span class="rich-swatch rich-swatch--{kind}" aria-hidden="true"></span>{_esc(text)}</li>'
        for kind, text in items
    )
    return f'<ul class="rich-legend">{entries}</ul><p class="rich-legend-note">{_esc(note)}</p>'


def trade_partner_flows():
    """Real per-partner import flows: (key, label, icon, owned, units/cycle,
    funds per unit). Units include the challenge-mode multiplier so they sum
    to exactly chain.imported_supply()."""
    rows = []
    for key, label, icon, owned, per_unit, cost in (
        ("link", "Trade Link", "\U0001F310", runstate.chain.trade_link_investment, IMPORT_SUPPLY_PER_UNIT, TRADE_LINK_COST),
        (
            "regional", "Regional Partner", "\U0001F69A", runstate.chain.regional_trade_investment,
            REGIONAL_IMPORT_SUPPLY_PER_UNIT, REGIONAL_TRADE_COST,
        ),
        (
            "overseas", "Overseas Consortium", "\U0001F6A2", runstate.chain.overseas_trade_investment,
            OVERSEAS_IMPORT_SUPPLY_PER_UNIT, OVERSEAS_TRADE_COST,
        ),
    ):
        rows.append((key, label, icon, owned, runstate.chain.partner_supply("trade" if key == "link" else key), cost / per_unit))
    return rows


def internal_measure_flows():
    """Real per-measure recovery flows (key, label, icon, owned, units/cycle),
    summing to exactly chain.internal_circular_supply()."""
    return [
        (key, spec["label"], spec["icon"], runstate.chain.circularity_investment[key], runstate.chain.measure_supply(key))
        for key, spec in CIRCULARITY_INVESTMENTS.items()
    ]


def _multiplier_note():
    return " (counted at 65% in the Circular design challenge)" if runstate.chain.challenge_mode else ""


def trade_network_visual_html():
    """H25b: the rich trade-network map. A hub-and-spoke SVG: three partners
    feeding the chain from the left, the internal recovery loop and new
    extraction above/below, and surplus export on the right. Node size and
    flow thickness scale with the real units per cycle."""
    partners = trade_partner_flows()
    internal = runstate.chain.internal_circular_supply()
    imported = runstate.chain.imported_supply()
    extraction = runstate.chain.new_extraction_needed()
    surplus = runstate.chain.exportable_surplus()
    need = runstate.chain.material_need()
    scale = max([need, internal, imported, extraction, surplus] + [p[4] for p in partners] + [1.0])
    mnote = _multiplier_note()

    hub = (430.0, 200.0)
    hub_r = 52.0
    parts = []

    # Flows first, so nodes draw on top of their ends.
    ys = {"link": 60.0, "regional": 200.0, "overseas": 340.0}
    nodes = []
    for key, label, icon, owned, units, funds_per_unit in partners:
        centre = (110.0, ys[key])
        radius = _node_radius(units, scale)
        tip = (
            f"{label}: {owned} owned, importing {_fmt(units)} units per cycle{mnote}. "
            f"Costs {funds_per_unit:.2f} funds per unit of supply."
        )
        parts.append(_svg_flow("trade", units, scale, _straight(centre, radius, hub, hub_r), tip))
        nodes.append(_svg_node("trade", centre, radius, icon, label, f"+{_fmt(units)}/cycle", tip))

    int_centre = (430.0, 48.0)
    int_r = _node_radius(internal, scale, base=24.0)
    int_tip = (
        f"Internal loop: repair, reuse and recycling return {_fmt(internal)} units per cycle to manufacturing"
        f"{mnote}."
    )
    parts.append(_svg_flow("internal", internal, scale, _straight(int_centre, int_r, hub, hub_r), int_tip))
    nodes.append(_svg_node("internal", int_centre, int_r, "♻️", "Internal loop",
                           f"+{_fmt(internal)}/cycle", int_tip, label_at="right"))

    ext_centre = (430.0, 352.0)
    ext_r = _node_radius(extraction, scale, base=24.0)
    ext_tip = (
        f"New extraction: {_fmt(extraction)} units per cycle of freshly mined material, the gap the loop "
        f"and trade supply do not cover."
    )
    parts.append(_svg_flow("extract", extraction, scale, _straight(ext_centre, ext_r, hub, hub_r), ext_tip))
    nodes.append(_svg_node("extract", ext_centre, ext_r, "⛏️", "New extraction",
                           f"{_fmt(extraction)}/cycle", ext_tip, label_at="right"))

    exp_centre = (750.0, 200.0)
    exp_r = _node_radius(surplus, scale)
    exp_tip = (
        f"Surplus export: {_fmt(surplus)} units per cycle of supply beyond this cycle's need are sold outward "
        f"at {EXPORT_PRICE_PER_UNIT:.0f} funds per unit."
    )
    parts.append(_svg_flow("export", surplus, scale, _straight(hub, hub_r, exp_centre, exp_r), exp_tip))
    nodes.append(_svg_node("export", exp_centre, exp_r, "\U0001F4B0", "Surplus export",
                           f"{_fmt(surplus)}/cycle", exp_tip))

    hub_tip = (
        f"Your chain: needs {_fmt(need)} units per cycle. Supply this cycle: {_fmt(internal)} internal "
        f"+ {_fmt(imported)} imported; {_fmt(extraction)} newly extracted; {_fmt(surplus)} surplus exported."
    )
    nodes.append(_svg_node("hub", hub, hub_r, "\U0001F3ED", "Your chain", f"needs {_fmt(need)}/cycle",
                           hub_tip, label_at="corner"))

    summary = (
        f"Trade network map. Your chain needs {_fmt(need)} units per cycle: {_fmt(internal)} from the internal "
        f"loop, {_fmt(imported)} imported from trade partners, {_fmt(extraction)} newly extracted, "
        f"{_fmt(surplus)} surplus exported. Focus any node or flow for details."
    )
    svg = (
        f'<svg class="rich-svg" viewBox="0 0 860 430" role="group" aria-label="{_esc(summary)}" '
        f'xmlns="http://www.w3.org/2000/svg">' + "".join(parts) + "".join(nodes) + "</svg>"
    )
    legend = _legend_html(
        [
            ("trade", "Imported from a trade partner"),
            ("internal", "Internal loop (repair, reuse, recycling)"),
            ("extract", "New extraction"),
            ("export", "Surplus sold outward"),
        ],
        "Node size and line thickness scale with units per cycle. Animated dashes show direction; "
        "with reduced motion on, the arrowheads show it instead.",
    )
    caption = f'<p class="rich-caption">{_esc(summary.replace("Trade network map. ", ""))}</p>'
    return caption + svg + legend


def supply_map_visual_html():
    """H29b: the rich circular supply chain map. Four stages around a
    diamond (Extract, Manufacture, Use, Discard), the goods flow between
    them, three proportional return lanes from Discard back to Manufacture
    (repair, reuse, recycling), trade imports and surplus export at the top."""
    need = runstate.chain.material_need()
    extraction = runstate.chain.new_extraction_needed()
    internal_rows = internal_measure_flows()
    internal = runstate.chain.internal_circular_supply()
    imported = runstate.chain.imported_supply()
    surplus = runstate.chain.exportable_surplus()
    unrecovered = max(0.0, need - internal)
    scale = max([need, extraction, imported, surplus] + [row[4] for row in internal_rows] + [1.0])
    mnote = _multiplier_note()

    r = 38.0
    manuf = (430.0, 95.0)
    use = (640.0, 245.0)
    discard = (430.0, 395.0)
    extract = (220.0, 245.0)
    trade_node = (100.0, 95.0)
    export_node = (760.0, 95.0)
    parts, nodes = [], []

    ext_tip = f"Extract to Manufacture: {_fmt(extraction)} units per cycle of newly extracted material."
    parts.append(_svg_flow("extract", extraction, scale, _straight(extract, r, manuf, r), ext_tip))
    goods_tip = f"Goods: {_fmt(need)} units per cycle of material made into goods and put to use."
    parts.append(_svg_flow("goods", need, scale, _straight(manuf, r, use, r), goods_tip))
    disc_tip = f"Use to Discard: {_fmt(need)} units per cycle of goods reach the end of their life."
    parts.append(_svg_flow("goods", need, scale, _straight(use, r, discard, r), disc_tip))

    # Three return lanes Discard -> Manufacture, bowed apart so thick lines
    # never overlap; each ends on the node's edge at its own offset.
    for row, bow in zip(internal_rows, (-90.0, 0.0, 90.0)):
        key, label, icon, owned, units = row
        off = bow / 4.0
        dy = math.sqrt(max(r * r - off * off, 1.0))
        p0 = (discard[0] + off, discard[1] - dy)
        p3 = (manuf[0] + off, manuf[1] + dy)
        geometry = (p0, (430.0 + bow, 300.0), (430.0 + bow, 190.0), p3)
        tip = (
            f"{label}: {owned} owned, returning {_fmt(units)} units per cycle from Discard to "
            f"Manufacture{mnote}."
        )
        parts.append(_svg_flow(key, units, scale, geometry, tip))
        # Lane label sits beside the lane's midpoint.
        lx = 430.0 + bow * 0.75
        parts.append(
            f'<text class="rich-lane-label" x="{lx:.1f}" y="{228:.1f}" text-anchor="middle" aria-hidden="true">'
            f'{icon} {_fmt(units)}</text>'
        )

    trade_units = imported
    trade_tip = (
        f"Trade partners: {_fmt(imported)} units per cycle imported into Manufacture from all partners"
        f"{mnote}."
    )
    parts.append(_svg_flow("trade", trade_units, scale, _straight(trade_node, 34.0, manuf, r), trade_tip))
    exp_tip = (
        f"Surplus export: {_fmt(surplus)} units per cycle leave Manufacture, supply beyond this cycle's need, "
        f"sold at {EXPORT_PRICE_PER_UNIT:.0f} funds per unit."
    )
    parts.append(_svg_flow("export", surplus, scale, _straight(manuf, r, export_node, 34.0), exp_tip))

    stages = (
        ("stage", extract, "⛏️", "Extract", f"{_fmt(extraction)} new/cycle",
         f"Extract: {_fmt(extraction)} units per cycle of newly mined material, adding to lasting damage."),
        ("stage", manuf, "\U0001F3ED", "Manufacture", f"needs {_fmt(need)}/cycle",
         f"Manufacture: needs {_fmt(need)} units per cycle; receives {_fmt(extraction)} new, "
         f"{_fmt(internal)} internal, {_fmt(imported)} imported."),
        ("stage", use, "\U0001F6CD️", "Use", f"{_fmt(need)}/cycle",
         f"Use: {_fmt(need)} units per cycle of goods in use."),
        ("stage", discard, "\U0001F5D1️", "Discard", f"{_fmt(unrecovered)} not recovered",
         f"Discard: {_fmt(need)} units per cycle arrive; {_fmt(internal)} are recovered by repair, reuse and "
         f"recycling, {_fmt(unrecovered)} are not recovered internally this cycle."),
    )
    for kind, centre, icon, label, value, tip in stages:
        at = "above" if label == "Manufacture" else "below"
        nodes.append(_svg_node(kind, centre, r, icon, label, value, tip, label_at=at))
    nodes.append(_svg_node("trade", trade_node, 34.0, "\U0001F310", "Trade partners",
                           f"+{_fmt(imported)}/cycle", trade_tip))
    nodes.append(_svg_node("export", export_node, 34.0, "\U0001F4B0", "Surplus export",
                           f"{_fmt(surplus)}/cycle", exp_tip))

    share = runstate.chain.circular_fraction_this_cycle()
    summary = (
        f"Circular supply chain map. Production needs {_fmt(need)} units per cycle. Recovered internally: "
        + ", ".join(f"{row[1]} {_fmt(row[4])}" for row in internal_rows)
        + f". Imported {_fmt(imported)}, newly extracted {_fmt(extraction)}, surplus exported {_fmt(surplus)}. "
        f"Circular share this cycle {share * 100:.0f}%. Focus any stage or flow for details."
    )
    svg = (
        f'<svg class="rich-svg" viewBox="0 0 860 470" role="group" aria-label="{_esc(summary)}" '
        f'xmlns="http://www.w3.org/2000/svg">' + "".join(parts) + "".join(nodes) + "</svg>"
    )
    legend = _legend_html(
        [
            ("extract", "New extraction"),
            ("goods", "Goods through Manufacture, Use and Discard"),
            ("repair", "Repair returning to Manufacture"),
            ("reuse", "Reuse returning to Manufacture"),
            ("recycle", "Recycling returning to Manufacture"),
            ("trade", "Trade imports"),
            ("export", "Surplus export"),
        ],
        "Line thickness scales with units per cycle. Animated dashes show direction; with reduced motion on, "
        "the arrowheads show it instead.",
    )
    caption = f'<p class="rich-caption">{_esc(summary.replace("Circular supply chain map. ", ""))}</p>'
    return caption + svg + legend


# Opt-in toggles. `pref` is the localStorage key (via window.loopVisual in
# rich-maps.js); the choice is a browser preference, never part of a save.
VISUAL_VIEWS = {
    "trade": {
        "button": "trade-visual-toggle-button",
        "panel": "trade-visual",
        "body": "trade-visual-body",
        "note": "trade-visual-unsupported",
        "host": "trade-network",
        "host_class": "rich-trade-on",
        "pref": "loop-visual-trade",
        "builder": "trade_network_visual_html",
        "label": "network",
    },
    "chain": {
        "button": "supply-visual-toggle-button",
        "panel": "supply-visual",
        "body": "supply-visual-body",
        "note": "supply-visual-unsupported",
        "host": "network-map-panel",
        "host_class": "rich-chain-on",
        "pref": "loop-visual-chain",
        "builder": "supply_map_visual_html",
        "label": "supply chain",
    },
}
visual_view = {"trade": False, "chain": False}


def _visual_hook():
    """The optional rich-maps.js bridge (window.loopVisual): preference
    storage and an SVG-support check. Lazy import and getattr default so
    it is a safe no-op under pytest and on any page without the script."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return getattr(window, "loopVisual", None)


def _visual_supported():
    hook = _visual_hook()
    if hook is None:
        return True
    try:
        return bool(hook.supported())
    except Exception:  # noqa: BLE001 -- a broken bridge must never break the game
        return False


def _load_visual_prefs():
    hook = _visual_hook()
    if hook is None or not _visual_supported():
        return
    for kind, spec in VISUAL_VIEWS.items():
        try:
            visual_view[kind] = hook.get(spec["pref"]) == "1"
        except Exception:  # noqa: BLE001
            visual_view[kind] = False


def _save_visual_pref(kind):
    hook = _visual_hook()
    if hook is None:
        return
    try:
        hook.set(VISUAL_VIEWS[kind]["pref"], "1" if visual_view[kind] else "0")
    except Exception:  # noqa: BLE001
        pass


def render_visual_views():
    """Syncs both opt-in views with the live state. Only builds the SVG for
    a view that is switched on; an off view is emptied so nothing stale
    lingers."""
    supported = _visual_supported()
    for kind, spec in VISUAL_VIEWS.items():
        asked = visual_view[kind]
        on = asked and supported
        button = document.getElementById(spec["button"])
        panel = document.getElementById(spec["panel"])
        body = document.getElementById(spec["body"])
        host = document.getElementById(spec["host"])
        button.innerText = (
            f"\U0001F3A8 Hide visual {spec['label']} view" if asked else f"\U0001F3A8 Show visual {spec['label']} view"
        )
        button.setAttribute("aria-pressed", "true" if asked else "false")
        # The panel shows whenever the player asked for the visual view, so
        # its notes (unsupported here / needs a wider screen) stay visible
        # even where the drawing itself cannot appear.
        panel.hidden = not asked
        document.getElementById(spec["note"]).hidden = supported
        if on:
            host.classList.add(spec["host_class"])
            body.innerHTML = globals()[spec["builder"]]()
        else:
            host.classList.remove(spec["host_class"])
            body.innerHTML = ""


def _make_visual_toggle_handler(kind):
    def handler(event=None):
        visual_view[kind] = not visual_view[kind]
        _save_visual_pref(kind)
        render_visual_views()

    return handler
