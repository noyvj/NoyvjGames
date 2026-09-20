"""Continuum -- K1/K24/K28: the optional "City Views" panel's data and drawings.

Three read-only views of the same live city, all pure functions of a
`CityState` (plus the current research effects and last season's report),
so they are testable without a DOM and can never change the simulation:

- K1 `dashboard()`: a dense, numbers-first readout of every stat at once.
- K24 `civic_map_svg()`: a simplified 2D top-down schematic of the built
  settlement, one "district" per building type. Each building is one glyph;
  every district has a text label and a distinct glyph shape, so nothing is
  encoded by colour alone.
- K28 `flow_svg()`: a Sankey-style diagram of last season's production chain
  (workers -> what they made -> where it went). The flow values come from the
  season report; the per-role split of a shared resource is by base yield
  (workers x the role's base output), which is an honest approximation and is
  labelled as such in the UI.

Nothing here is saved, so there is no save-robustness surface; malformed
inputs (a missing report, odd numbers) degrade to empty output.
"""

import math

import sim
import sustainability

# --- K1: the dashboard --------------------------------------------------


def _num(value, fmt="{:.1f}"):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    if not math.isfinite(value):
        return "-"
    return fmt.format(value)


def dashboard(state, effects, researched=None):
    """Sections of (label, value) rows covering every stat at once.

    `researched` is an optional (done, total) pair for the research tree.
    Returns a list of {"title": str, "rows": [(label, text), ...]}.
    """
    ev = sustainability.evaluate(state, effects)
    hard = sustainability.is_hard_mode(state)
    report = state.last_report if isinstance(state.last_report, dict) else {}
    era_i = sim.era_index(state.era)
    housing = state.housing_capacity(effects)
    storage = state.food_storage_capacity(effects)

    sections = []
    sections.append(
        {
            "title": "Settlement",
            "rows": [
                ("Era", sim.ERA_LABEL[state.era]),
                ("Season", str(state.season)),
                ("People", str(state.population)),
                ("Shelter capacity", _num(housing, "{:.0f}")),
                ("Unassigned workers", str(state.idle_workers())),
                ("Growth progress", _num(state.growth_progress * 100, "{:.0f}%")),
                ("Calm seasons in a row", str(state.calm_streak)),
            ],
        }
    )
    sections.append(
        {
            "title": "Stores",
            "rows": [
                ("Food", f"{_num(state.resources['food'], '{:.0f}')} / {_num(storage, '{:.0f}')}"),
                ("Materials", _num(state.resources["materials"], "{:.0f}")),
                ("Tools", _num(state.resources["tools"])),
                ("Knowledge", _num(state.resources["knowledge"])),
                ("Surplus", _num(state.resources["surplus"])),
            ],
        }
    )
    sections.append(
        {
            "title": "Land",
            "rows": [
                ("Land health", _num(state.land_health * 100, "{:.0f}%")),
                ("Taken last season", _num(state.last_extraction)),
                ("Sustainable yield", _num(state.last_sustainable_yield)),
            ],
        }
    )
    sections.append(
        {
            "title": "Sustainability",
            "rows": [
                ("Score", f"{_num(ev['score'], '{:.0f}')} / 100 ({sustainability.score_label(ev['score'], hard)})"),
                ("Livability", _num(ev["components"]["livability"], "{:.0f}")),
                ("Equity", _num(ev["components"]["equity"], "{:.0f}")),
                ("Resource balance", _num(ev["components"]["balance"], "{:.0f}")),
                ("Resilience", _num(ev["components"]["resilience"], "{:.0f}")),
            ],
        }
    )
    sections.append(
        {
            "title": "Workforce",
            "rows": [
                (sim.ROLE_LABEL[r], str(state.allocation.get(r, 0))) for r in sim.roles_for_era(state.era)
            ],
        }
    )
    sections.append(
        {
            "title": "Buildings",
            "rows": [
                (sim.BUILDING_LABEL[b], str(state.buildings.get(b, 0))) for b in sim.buildings_for_era(state.era)
            ],
        }
    )
    last = []
    if report:
        last = [
            ("Food gathered", _num(report.get("food_gathered"))),
            ("Materials gathered", _num(report.get("materials_gathered"))),
            ("Tools made", _num(report.get("tools_made"))),
            ("Knowledge made", _num(report.get("knowledge_made"))),
            ("People fed", _num(float(report.get("fed_fraction", 1.0)) * 100, "{:.0f}%")),
            ("Born / lost", f"{report.get('births', 0)} / {report.get('deaths', 0)}"),
            ("Food spoiled", _num(report.get("spoiled"))),
        ]
    else:
        last = [("Last season", "no season played yet")]
    sections.append({"title": "Last season", "rows": last})

    pressures = []
    if era_i >= sim.era_index("classical") and state.buildings.get("canals", 0) > 0:
        pressures.append(("Canal staffing", _num(float(report.get("canal_staffing_ratio", 0.0)) * 100, "{:.0f}%")))
    if era_i >= sim.era_index("medieval"):
        pressures.append(("Public works cover", _num(float(report.get("public_works_coverage_ratio", 0.0)) * 100, "{:.0f}%")))
    if era_i >= sim.era_index("industrial"):
        pressures.append(("Pollution", _num(state.pollution * 100, "{:.0f}%")))
    if era_i >= sim.era_index("digital"):
        pressures.append(("Sprawl", _num(state.sprawl * 100, "{:.0f}%")))
    if era_i >= sim.era_index("space"):
        pressures.append(("Habitat layout", _num(float(report.get("habitat_layout_ratio", 0.0)) * 100, "{:.0f}%")))
    if pressures:
        sections.append({"title": "Era pressures", "rows": pressures})
    if researched is not None:
        sections.append({"title": "Research", "rows": [("Discoveries", f"{researched[0]} of {researched[1]}")]})
    return sections


# --- K24: civic infrastructure map --------------------------------------
# One glyph shape per building type, so the map never leans on colour.
GLYPH_SHAPES = {
    "shelter": "square",
    "granary": "circle",
    "hearth": "triangle",
    "toolworks": "diamond",
    "farmland": "bars",
    "canals": "wave",
    "public_works": "cross",
    "sanitation_works": "ring",
    "transit_hubs": "hex",
    "habitat_rings": "double_ring",
}

DISTRICT_W = 70
DISTRICT_H = 88
DISTRICT_COLS = 5
CELL = 14
CELLS_PER_ROW = 4
MAX_GLYPHS = 16  # per district; the rest are counted in text


def _glyph(shape, cx, cy):
    r = 5.0
    if shape == "square":
        return f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r}" height="{2 * r}" class="map-glyph"/>'
    if shape == "circle":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" class="map-glyph"/>'
    if shape == "triangle":
        return f'<polygon points="{cx:.1f},{cy - r:.1f} {cx + r:.1f},{cy + r:.1f} {cx - r:.1f},{cy + r:.1f}" class="map-glyph"/>'
    if shape == "diamond":
        return f'<polygon points="{cx:.1f},{cy - r:.1f} {cx + r:.1f},{cy:.1f} {cx:.1f},{cy + r:.1f} {cx - r:.1f},{cy:.1f}" class="map-glyph"/>'
    if shape == "bars":
        return (
            f'<path d="M{cx - r:.1f},{cy - 3:.1f}h{2 * r} M{cx - r:.1f},{cy:.1f}h{2 * r} M{cx - r:.1f},{cy + 3:.1f}h{2 * r}" '
            f'class="map-glyph map-glyph--line"/>'
        )
    if shape == "wave":
        return (
            f'<path d="M{cx - r:.1f},{cy:.1f} q{r / 2:.1f},-5 {r:.1f},0 t{r:.1f},0" class="map-glyph map-glyph--line"/>'
        )
    if shape == "cross":
        return (
            f'<path d="M{cx:.1f},{cy - r:.1f}v{2 * r} M{cx - r:.1f},{cy:.1f}h{2 * r}" class="map-glyph map-glyph--line"/>'
        )
    if shape == "ring":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" class="map-glyph map-glyph--hollow"/>'
    if shape == "hex":
        pts = " ".join(
            f"{cx + r * math.cos(math.radians(60 * k)):.1f},{cy + r * math.sin(math.radians(60 * k)):.1f}"
            for k in range(6)
        )
        return f'<polygon points="{pts}" class="map-glyph"/>'
    # double_ring
    return (
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" class="map-glyph map-glyph--hollow"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r / 2:.1f}" class="map-glyph map-glyph--hollow"/>'
    )


def map_districts(state):
    """The districts the map draws: [(building_id, count)], oldest era first."""
    out = []
    for b in sim.buildings_for_era(state.era):
        try:
            count = max(0, int(state.buildings.get(b, 0)))
        except (TypeError, ValueError, OverflowError):
            count = 0
        out.append((b, count))
    return out


def civic_map_svg(state):
    """The K24 schematic as an SVG string."""
    districts = map_districts(state)
    if not districts:
        return ""
    cols = min(DISTRICT_COLS, len(districts))
    rows = math.ceil(len(districts) / DISTRICT_COLS)
    width = cols * DISTRICT_W + 8
    height = rows * DISTRICT_H + 8
    parts = [
        f'<svg viewBox="0 0 {width} {height}" class="views-svg" role="img" '
        f'aria-label="Top-down schematic of the settlement: one district per building type">',
        f'<rect x="0" y="0" width="{width}" height="{height}" class="map-bg"/>',
    ]
    for i, (building, count) in enumerate(districts):
        x0 = 4 + (i % DISTRICT_COLS) * DISTRICT_W
        y0 = 4 + (i // DISTRICT_COLS) * DISTRICT_H
        cls = "map-district" if count else "map-district map-district--empty"
        parts.append(f'<rect x="{x0 + 2}" y="{y0 + 2}" width="{DISTRICT_W - 4}" height="{DISTRICT_H - 4}" rx="4" class="{cls}"/>')
        label = sim.BUILDING_LABEL[building]
        parts.append(f'<text x="{x0 + DISTRICT_W / 2}" y="{y0 + 15}" class="map-label" text-anchor="middle">{label}</text>')
        shown = min(count, MAX_GLYPHS)
        for k in range(shown):
            cx = x0 + 8 + CELL / 2 + (k % CELLS_PER_ROW) * CELL
            cy = y0 + 28 + CELL / 2 + (k // CELLS_PER_ROW) * CELL
            parts.append(_glyph(GLYPH_SHAPES[building], cx, cy))
        count_text = str(count) if count <= MAX_GLYPHS else f"{count} (showing {MAX_GLYPHS})"
        parts.append(f'<text x="{x0 + DISTRICT_W / 2}" y="{y0 + DISTRICT_H - 8}" class="map-count" text-anchor="middle">{count_text}</text>')
    parts.append("</svg>")
    return "".join(parts)


def map_caption(state):
    districts = map_districts(state)
    total = sum(c for _, c in districts)
    shelters = dict(districts).get("shelter", 0)
    if shelters > 0:
        density = f"{state.population / shelters:.1f} people per shelter"
    else:
        density = "no shelters built"
    return f"{total} buildings across {len(districts)} districts, {state.population} people, {density}."


# --- K28: resource flow diagram -----------------------------------------
# role -> (resource it feeds, base yield weight)
ROLE_FEEDS = {
    "foragers": ("food", sim.FOOD_PER_FORAGER),
    "farmers": ("food", sim.FOOD_PER_FARMER),
    "gatherers": ("materials", sim.MATERIALS_PER_GATHERER),
    "factory_workers": ("materials", sim.MATERIALS_PER_FACTORY_WORKER),
    "crafters": ("tools", sim.TOOLS_PER_CRAFTER),
    "guildmasters": ("tools", sim.TOOLS_PER_GUILDMASTER),
    "keepers": ("knowledge", sim.KNOWLEDGE_PER_KEEPER),
}

RESOURCE_LABEL = {"food": "Food", "materials": "Materials", "tools": "Tools", "knowledge": "Knowledge"}


def _f(report, key):
    try:
        value = float(report.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) and value > 0 else 0.0


def flow_links(state, report):
    """(source_id, target_id, value) links plus a node-label map.

    Returns (links, labels). Empty when there is no report yet. Conserves
    flow at every middle node: what leaves a resource never exceeds what
    entered it.
    """
    if not isinstance(report, dict) or not report:
        return [], {}
    produced = {
        "food": _f(report, "food_gathered"),
        "materials": _f(report, "materials_gathered"),
        "tools": _f(report, "tools_made"),
        "knowledge": _f(report, "knowledge_made"),
    }
    labels = {}
    links = []
    # workers -> resource, split by base yield
    weights = {}
    for role in sim.roles_for_era(state.era):
        feed = ROLE_FEEDS.get(role)
        if not feed:
            continue
        workers = max(0, int(state.allocation.get(role, 0)))
        if workers:
            weights.setdefault(feed[0], []).append((role, workers * feed[1]))
    for resource, entries in weights.items():
        total_w = sum(w for _, w in entries)
        if total_w <= 0 or produced[resource] <= 0:
            continue
        for role, w in entries:
            links.append((f"role:{role}", f"res:{resource}", produced[resource] * w / total_w))
            labels[f"role:{role}"] = f"{sim.ROLE_LABEL[role]} ({int(state.allocation[role])})"
    # resource -> use
    remaining = produced["food"]
    for key, target, text in (
        ("food_consumed", "use:eaten", "Eaten"),
        ("spoiled", "use:spoiled", "Spoiled"),
        ("surplus_banked", "use:banked", "Banked as surplus"),
    ):
        amount = min(_f(report, key), remaining)
        if amount > 0:
            links.append(("res:food", target, amount))
            labels[target] = text
            remaining -= amount
    if remaining > 0.05:
        links.append(("res:food", "use:food_kept", remaining))
        labels["use:food_kept"] = "Kept in stores"
    spent = min(_f(report, "tools_made") * sim.MATERIALS_PER_TOOL, produced["materials"])
    if spent > 0:
        links.append(("res:materials", "use:tools_made", spent))
        labels["use:tools_made"] = "Made into tools"
    if produced["materials"] - spent > 0.05:
        links.append(("res:materials", "use:materials_kept", produced["materials"] - spent))
        labels["use:materials_kept"] = "Materials kept"
    if produced["tools"] > 0:
        links.append(("res:tools", "use:tools_stock", produced["tools"]))
        labels["use:tools_stock"] = "Added to tool stock"
    if produced["knowledge"] > 0:
        links.append(("res:knowledge", "use:research", produced["knowledge"]))
        labels["use:research"] = "Added to knowledge"
    # resource nodes only exist if something flows through them
    for res in RESOURCE_LABEL:
        if any(s == f"res:{res}" or t == f"res:{res}" for s, t, _ in links):
            labels[f"res:{res}"] = f"{RESOURCE_LABEL[res]} {produced[res]:.1f}"
    # a resource with output but no workers to attribute it to still shows
    return [l for l in links if l[2] > 0], labels


NODE_W = 100
COL_X = (0, 130, 260)
FLOW_W = 360
FLOW_H = 190
NODE_GAP = 6
MIN_NODE_H = 15


def flow_svg(state, report):
    """The K28 Sankey-style diagram as an SVG string ('' before season 1 ends)."""
    links, labels = flow_links(state, report)
    if not links:
        return ""
    cols = [[], [], []]
    for node in labels:
        kind = node.split(":", 1)[0]
        cols[{"role": 0, "res": 1, "use": 2}[kind]].append(node)
    # stable, meaningful order: resources in canonical order; others by first appearance in links
    cols[1].sort(key=lambda n: list(RESOURCE_LABEL).index(n.split(":", 1)[1]))
    for c in (0, 2):
        seen = []
        for s, t, _ in links:
            for n in (s, t):
                if n in cols[c] and n not in seen:
                    seen.append(n)
        cols[c] = seen

    def throughput(node):
        out_v = sum(v for s, _, v in links if s == node)
        in_v = sum(v for _, t, v in links if t == node)
        return max(out_v, in_v)

    heights_units = [sum(throughput(n) for n in col) for col in cols]
    tallest_gapless = FLOW_H - NODE_GAP * (max(len(c) for c in cols) + 1)
    scale = tallest_gapless / max(max(heights_units), 1e-9)
    # Nodes taller than their flow need a min height, which can push a
    # column past FLOW_H, so shrink the scale until every column fits.
    for _ in range(20):
        fits = all(
            sum(max(throughput(n) * scale, MIN_NODE_H) for n in col) + NODE_GAP * (len(col) + 1) <= FLOW_H
            for col in cols
        )
        if fits:
            break
        scale *= 0.85
    pos = {}
    for ci, col in enumerate(cols):
        used = sum(max(throughput(n) * scale, MIN_NODE_H) for n in col) + NODE_GAP * (len(col) - 1 if col else 0)
        y = (FLOW_H - used) / 2
        for n in col:
            h = max(throughput(n) * scale, MIN_NODE_H)
            pos[n] = (COL_X[ci], y, h)
            y += h + NODE_GAP
    out_off = {n: 0.0 for n in pos}
    in_off = {n: 0.0 for n in pos}
    ribbons = []
    for s, t, v in sorted(links, key=lambda l: (list(pos).index(l[0]), list(pos).index(l[1]))):
        h = v * scale
        sx, sy, _ = pos[s]
        tx, ty, _ = pos[t]
        y0 = sy + out_off[s]
        y1 = ty + in_off[t]
        out_off[s] += h
        in_off[t] += h
        x0 = sx + NODE_W
        x1 = tx
        mid = (x0 + x1) / 2
        resource = (s if s.startswith("res:") else t if t.startswith("res:") else "res:food").split(":", 1)[1]
        if s.startswith("res:") and t.startswith("use:"):
            resource = s.split(":", 1)[1]
        title = f"{labels[s]} to {labels[t]}: {v:.1f}"
        ribbons.append(
            f'<path d="M{x0:.1f},{y0:.1f} C{mid:.1f},{y0:.1f} {mid:.1f},{y1:.1f} {x1:.1f},{y1:.1f} '
            f'L{x1:.1f},{y1 + h:.1f} C{mid:.1f},{y1 + h:.1f} {mid:.1f},{y0 + h:.1f} {x0:.1f},{y0 + h:.1f} Z" '
            f'class="flow-ribbon flow-ribbon--{resource}"><title>{title}</title></path>'
        )
    nodes = []
    for n, (x, y, h) in pos.items():
        text = labels[n]
        if n.startswith("use:"):
            value = sum(v for _, t, v in links if t == n)
            text = f"{text} {value:.1f}"
        nodes.append(
            f'<rect x="{x}" y="{y:.1f}" width="{NODE_W}" height="{h:.1f}" rx="3" class="flow-node"/>'
            f'<text x="{x + NODE_W / 2}" y="{y + h / 2 + 3.5:.1f}" class="flow-label" text-anchor="middle">{text}</text>'
        )
    return (
        f'<svg viewBox="0 0 {FLOW_W} {FLOW_H}" class="views-svg" role="img" '
        f'aria-label="Flow diagram of last season: workers, what they produced, and where it went">'
        f'<rect x="0" y="0" width="{FLOW_W}" height="{FLOW_H}" class="map-bg"/>'
        + "".join(ribbons)
        + "".join(nodes)
        + "</svg>"
    )


def flow_caption(report):
    if not isinstance(report, dict) or not report:
        return "Advance a season to see how the settlement's work turned into food, materials, tools and knowledge."
    note = "Widths are proportional to units per season. Where several roles feed one resource, the split is by base yield."
    if _f(report, "food_consumed") > _f(report, "food_gathered") + 0.05:
        note += " The settlement ate more than it gathered and drew down its stores."
    return note
