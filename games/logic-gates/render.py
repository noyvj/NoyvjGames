"""Logic Gates -- draws the board as SVG. Chips are placed by depth (no dragging), so the picture is a pure function of the circuit.

Every pin carries data-pin ("s:..." for a source, "d:..." for something that takes a wire) so the page can wire by tapping. A wire that
carries 1 is solid and thick, a wire that carries 0 is thin and dashed: the meaning is in the shape, colour is decoration."""

from html import escape

from levels import REGISTRY
from words import TIE_TIPS

CHIP_W = 112
COL_GAP = 92
ROW_GAP = 18
PIN_PITCH = 20
HEAD = 24
NODE_W = 64
NODE_H = 34
MARGIN = 14


def depths(circuit):
    chips = {c["id"]: c for c in circuit["chips"] if c["type"] in REGISTRY}
    memo, visiting = {}, set()

    def depth(cid):
        if cid in memo:
            return memo[cid]
        if cid in visiting:
            return -1
        visiting.add(cid)
        best = 0
        d = REGISTRY[chips[cid]["type"]]
        for pin in d["ins"]:
            src = circuit["wires"].get(f"{cid}.{pin}")
            if src and not src.startswith(("in:", "const:")):
                sid = int(src.split(".")[0]) if src.split(".")[0].isdigit() else None
                if sid in chips and sid != cid:
                    sd = depth(sid)
                    if sd >= 0:
                        best = max(best, sd + 1)
        visiting.discard(cid)
        memo[cid] = best
        return best

    return {cid: depth(cid) for cid in chips}


def chip_height(d):
    return HEAD + PIN_PITCH * max(len(d["ins"]), len(d["outs"])) + 6


def layout(level, circuit):
    """-> (positions, width, height). positions: key -> (x, y, w, h); keys: ("in", name), ("out", name), ("const", "0"), ("chip", id)."""
    dep = depths(circuit)
    chips = [c for c in circuit["chips"] if c["id"] in dep]
    ncols = (max(dep.values()) + 1) if dep else 0
    col_w = []
    for k in range(ncols):
        ws = [max(CHIP_W, 9 * len(REGISTRY[c["type"]]["label"]) + 34) for c in chips if dep[c["id"]] == k]
        col_w.append(max(ws))
    pos = {}
    x = MARGIN
    y = MARGIN
    for name in level["ins"]:
        pos[("in", name)] = (x, y, NODE_W, NODE_H)
        y += NODE_H + ROW_GAP
    for v in ("0", "1"):
        pos[("const", v)] = (x, y, NODE_W - 16, 26)
        y += 26 + ROW_GAP
    height = y
    x += NODE_W + COL_GAP
    col_x = []
    for k in range(ncols):
        col_x.append(x)
        yy = MARGIN
        for c in chips:
            if dep[c["id"]] == k:
                h = chip_height(REGISTRY[c["type"]])
                pos[("chip", c["id"])] = (x, yy, col_w[k], h)
                yy += h + ROW_GAP
        height = max(height, yy)
        x += col_w[k] + COL_GAP
    y = MARGIN
    for name in level["outs"]:
        pos[("out", name)] = (x, y, NODE_W, NODE_H)
        y += NODE_H + ROW_GAP
    height = max(height, y)
    return pos, x + NODE_W + MARGIN, height + MARGIN - ROW_GAP


def source_point(src, pos):
    if src.startswith("in:"):
        x, y, w, h = pos[("in", src[3:])]
        return x + w, y + h / 2
    if src.startswith("const:"):
        x, y, w, h = pos[("const", src[6:])]
        return x + w, y + h / 2
    cid, _, pin = src.partition(".")
    key = ("chip", int(cid))
    if key not in pos:
        return None
    x, y, w, h = pos[key]
    d_outs = None
    return x + w, y + HEAD + PIN_PITCH * (_out_index(cid, pin, d_outs)) + PIN_PITCH / 2


_CIRCUIT = {}


def _out_index(cid, pin, _unused):
    chip = _CIRCUIT.get(int(cid))
    return REGISTRY[chip["type"]]["outs"].index(pin) if chip else 0


def dest_point(dest, pos, circuit):
    if dest.startswith("out:"):
        x, y, w, h = pos[("out", dest[4:])]
        return x, y + h / 2
    cid, _, pin = dest.partition(".")
    key = ("chip", int(cid))
    if key not in pos:
        return None
    chip = _CIRCUIT.get(int(cid))
    x, y, w, h = pos[key]
    return x, y + HEAD + PIN_PITCH * REGISTRY[chip["type"]]["ins"].index(pin) + PIN_PITCH / 2


def draw(level, circuit, values, inputs, armed=None, target=None):
    """values(src) -> 0/1 for a source string. inputs: the probe switch positions. -> (svg string, natural width)."""
    _CIRCUIT.clear()
    _CIRCUIT.update({c["id"]: c for c in circuit["chips"] if c["type"] in REGISTRY})
    pos, width, height = layout(level, circuit)
    out = [f'<svg id="lg-board" class="lg-board" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
           f'width="{width:.0f}" height="{height:.0f}" role="img" aria-labelledby="lg-board-title"><title id="lg-board-title">The circuit board</title>']
    wires, nodes = [], []
    for dest, src in circuit["wires"].items():
        a = source_point(src, pos)
        b = dest_point(dest, pos, circuit)
        if a is None or b is None:
            continue
        v = values(src)
        dx = max(30.0, abs(b[0] - a[0]) * 0.5)
        cls = "lg-w1" if v else "lg-w0"
        wires.append(f'<path class="lg-wire {cls}" d="M{a[0]:.1f},{a[1]:.1f} C{a[0] + dx:.1f},{a[1]:.1f} {b[0] - dx:.1f},{b[1]:.1f} {b[0]:.1f},{b[1]:.1f}"/>')

    def pin(kind, ident, x, y, cls=""):
        pid = f"{kind}:{ident}"
        mark = " lg-armed" if (kind == "s" and armed == ident) or (kind == "d" and target == ident) else ""
        return f'<circle class="lg-pin lg-pin-{kind}{mark}{cls}" data-pin="{escape(pid)}" cx="{x:.1f}" cy="{y:.1f}" r="7"/>'

    for name in level["ins"]:
        x, y, w, h = pos[("in", name)]
        on = 1 if inputs.get(name) else 0
        nodes.append(f'<g class="lg-node lg-switch{" lg-on" if on else ""}" data-flip="{escape(name)}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
                     f'<text x="{x + 10}" y="{y + h / 2 + 5}">{escape(name)}</text><text class="lg-val" x="{x + w - 22}" y="{y + h / 2 + 5}">{on}</text></g>')
        nodes.append(pin("s", f"in:{name}", x + w, y + h / 2))
    for v in ("0", "1"):
        x, y, w, h = pos[("const", v)]
        nodes.append(f'<g class="lg-node lg-const"><title>{escape(TIE_TIPS[v])}</title><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/><text x="{x + 8}" y="{y + h / 2 + 5}">tie {v}</text></g>')
        nodes.append(pin("s", f"const:{v}", x + w, y + h / 2))
    for chip in circuit["chips"]:
        key = ("chip", chip["id"])
        if key not in pos:
            continue
        d = REGISTRY[chip["type"]]
        x, y, w, h = pos[key]
        nodes.append(f'<g class="lg-node lg-chip lg-chip-{escape(d["kind"])}" data-chip="{chip["id"]}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9"/>'
                     f'<text class="lg-chip-label" x="{x + w / 2}" y="{y + 16}" text-anchor="middle">{escape(d["label"])} #{chip["id"]}</text></g>')
        for i, p in enumerate(d["ins"]):
            py = y + HEAD + PIN_PITCH * i + PIN_PITCH / 2
            floating = f"{chip['id']}.{p}" not in circuit["wires"]
            nodes.append(f'<text class="lg-pin-name" x="{x + 12}" y="{py + 4}">{escape(p)}</text>')
            nodes.append(pin("d", f"{chip['id']}.{p}", x, py, " lg-floating" if floating else ""))
        for i, p in enumerate(d["outs"]):
            py = y + HEAD + PIN_PITCH * i + PIN_PITCH / 2
            nodes.append(f'<text class="lg-pin-name" x="{x + w - 12}" y="{py + 4}" text-anchor="end">{escape(p)}</text>')
            nodes.append(pin("s", f"{chip['id']}.{p}", x + w, py))
    for name in level["outs"]:
        x, y, w, h = pos[("out", name)]
        src = circuit["wires"].get("out:" + name)
        on = 1 if src and values(src) else 0
        floating = src is None
        nodes.append(f'<g class="lg-node lg-lamp{" lg-on" if on else ""}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2:.0f}"/>'
                     f'<text x="{x + 24}" y="{y + h / 2 + 5}">{escape(name)}</text><text class="lg-val" x="{x + w - 16}" y="{y + h / 2 + 5}">{on}</text></g>')
        nodes.append(pin("d", f"out:{name}", x, y + h / 2, " lg-floating" if floating else ""))
    out.extend(wires)
    out.extend(nodes)
    out.append("</svg>")
    return "".join(out), width
