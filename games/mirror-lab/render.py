"""Mirror Lab -- the bench and the relay map, drawn as SVG strings by the engine so the markup is unit-tested and the page only
inserts it. Nothing here decides a rule: it draws what optics.trace() found.

No state is told by colour alone. A beam of each kind has its own dash pattern AND a letter (white solid, S short dashes with an "S",
L long dashes with an "L"); a lit sensor is filled with a tick, an unlit one hollow; a slot is a dashed square; a piece has its own
shape; a flipped mirror or prism is a mirror image of the other.
"""

import math

import optics

U = 56                      # one cell, in SVG units
PAD = 6
HALF = U // 2


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _pts(points):
    return " ".join("%s,%s" % (x, y) for x, y in points)


def _octagon(radius):
    out = []
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        out.append((round(HALF + radius * math.cos(a), 1), round(HALF + radius * math.sin(a), 1)))
    return out


def glyph(piece, state=0, fixed=False):
    """The inside of a piece's 56 x 56 cell (local coordinates)."""
    if piece == "mirror":
        body = '<polygon class="m-body" points="%s"/><polygon class="m-face" points="%s"/>' % (
            _pts([(7, 41), (41, 7), (49, 15), (15, 49)]), _pts([(7, 41), (41, 7), (44, 10), (10, 44)]))
        bolts = '<circle class="m-bolt" cx="12" cy="44" r="2.5"/><circle class="m-bolt" cx="44" cy="12" r="2.5"/>' if fixed else ""
        inner = body + bolts
        if state == 1:
            inner = '<g transform="translate(56 0) scale(-1 1)">' + inner + "</g>"
        return inner
    if piece == "splitter":
        return ('<polygon class="p-split" points="%s"/><polygon class="p-split-in" points="%s"/>'
                '<text class="p-mark" x="28" y="34" text-anchor="middle">&#189;</text>') % (
            _pts([(28, 5), (51, 28), (28, 51), (5, 28)]), _pts([(28, 12), (44, 28), (28, 44), (12, 28)]))
    if piece == "prism":
        inner = ('<polygon class="p-prism" points="%s"/><polygon class="p-prism-lit" points="%s"/>'
                 '<text class="p-mark" x="26" y="42" text-anchor="middle">P</text>') % (
            _pts([(8, 48), (48, 48), (20, 8)]), _pts([(20, 8), (8, 48), (22, 48)]))
        if state == 1:
            inner = '<g transform="translate(56 0) scale(-1 1)">' + inner + "</g>"
        return inner
    if piece == "absorber":
        return ('<polygon class="p-abs" points="%s"/><path class="p-abs-hatch" d="M12 40 L40 12 M20 46 L46 20 M12 28 L28 12 M28 46 L46 28"/>') % _pts(
            [(9, 9), (47, 9), (47, 47), (9, 47)])
    if piece in ("filter_s", "filter_l"):
        letter = "S" if piece == "filter_s" else "L"
        return ('<circle class="p-filter p-filter-%s" cx="28" cy="28" r="19"/><circle class="p-filter-in" cx="28" cy="28" r="12"/>'
                '<text class="p-mark" x="28" y="34" text-anchor="middle">%s</text>') % (letter.lower(), letter)
    return ""


def piece_icon(piece, state=0):
    return '<svg class="ml-icon" viewBox="0 0 56 56" aria-hidden="true" focusable="false">%s</svg>' % glyph(piece, state)


def state_words(piece, state):
    """The state of a piece in a few words ("" for a piece with one state)."""
    if piece == "mirror":
        return "slash" if state == 0 else "backslash"
    if piece == "prism":
        return "S beam leaves on the %s of its travel" % ("left" if state == 0 else "right")
    return ""


def piece_words(piece, state):
    extra = state_words(piece, state)
    return optics_label(piece) + (", " + extra if extra else "")


def optics_label(piece):
    return optics.PIECE_LABEL[piece].lower()


def _beam_points(seg):
    r, c, d_in, d_out, _kind, _born = seg
    cx, cy = PAD + c * U + HALF, PAD + r * U + HALF
    pts = []
    if d_in is not None:
        pts.append((cx - optics.DC[d_in] * HALF, cy - optics.DR[d_in] * HALF))
    pts.append((cx, cy))
    if d_out is not None:
        pts.append((cx + optics.DC[d_out] * HALF, cy + optics.DR[d_out] * HALF))
    return pts


def bench_svg(board, placed, tr, label=""):
    """The whole bench as one SVG string. `placed` is {(r, c): (piece, state)}; `tr` the optics.Trace of that layout."""
    width, height = PAD * 2 + board.w * U, PAD * 2 + board.h * U
    out = ['<svg class="ml-bench" viewBox="0 0 %d %d" role="img" aria-label="%s" focusable="false">' % (width, height, esc(label))]
    # floor, slots, walls
    for r in range(board.h):
        for c in range(board.w):
            x, y = PAD + c * U, PAD + r * U
            cell = (r, c)
            if cell in board.walls:
                out.append('<g class="ml-wall"><rect x="%d" y="%d" width="%d" height="%d" rx="3"/><path d="M%d %d L%d %d M%d %d L%d %d M%d %d L%d %d"/></g>' % (
                    x + 2, y + 2, U - 4, U - 4, x + 8, y + 40, x + 40, y + 8, x + 16, y + 50, x + 50, y + 16, x + 6, y + 24, x + 24, y + 6))
            else:
                out.append('<rect class="ml-cell" x="%d" y="%d" width="%d" height="%d"/>' % (x, y, U, U))
                if cell in board.slots:
                    out.append('<rect class="ml-slot" x="%d" y="%d" width="%d" height="%d" rx="7"/>' % (x + 4, y + 4, U - 8, U - 8))
    # beams (a wide faint underlay, then the beam itself)
    glow, lines, letters = [], [], []
    for seg in tr.segments:
        kind = seg[4]
        pts = _beam_points(seg)
        if len(pts) < 2:
            continue
        poly = _pts(pts)
        glow.append('<polyline class="ml-glow ml-glow-%s" points="%s"/>' % (kind, poly))
        lines.append('<polyline class="ml-beam ml-beam-%s" points="%s"/>' % (kind, poly))
        r, c, _d_in, d_out, _k, born = seg
        if kind != "W" and d_out is not None and (born or (r + c) % 3 == 0):
            cx, cy = PAD + c * U + HALF, PAD + r * U + HALF
            tx = cx + optics.DC[d_out] * 17 + (-optics.DR[d_out] * 8)
            ty = cy + optics.DR[d_out] * 17 + (optics.DC[d_out] * 8)
            letters.append('<text class="ml-letter ml-letter-%s" x="%.1f" y="%.1f" text-anchor="middle" dominant-baseline="central">%s</text>' % (kind, tx, ty, kind))
    out.extend(glow)
    out.extend(lines)
    out.extend(letters)
    # fixed mirrors
    for (r, c), state in sorted(board.fixed.items()):
        out.append('<g class="ml-fixed" transform="translate(%d %d)">%s</g>' % (PAD + c * U, PAD + r * U, glyph("mirror", state, True)))
    # emitters
    for r, c, d in board.emitters:
        out.append('<g class="ml-emitter" transform="translate(%d %d)"><rect class="e-body" x="8" y="8" width="40" height="40" rx="8"/>'
                   '<g transform="rotate(%d 28 28)"><polygon class="e-arrow" points="20,17 43,28 20,39"/></g></g>' % (PAD + c * U, PAD + r * U, (d - 1) * 90))
    # sensors
    for (r, c), need in sorted(board.sensors.items()):
        lit = (r, c) in tr.lit
        hit = (r, c) in tr.dark_hit
        x, y = PAD + c * U, PAD + r * U
        cls = "ml-sensor" + (" lit" if lit else "") + (" decoy" if need == "X" else "") + (" hit" if hit else "")
        inner = '<polygon class="s-body" points="%s"/>' % _pts(_octagon(20))
        if need == "X":
            inner += '<path class="s-cross" d="M19 19 L37 37 M37 19 L19 37"/>'
        elif lit:
            inner += '<circle class="s-lamp" cx="28" cy="28" r="9"/><path class="s-tick" d="M22 28 L27 33 L35 22"/>'
        else:
            inner += '<circle class="s-lamp" cx="28" cy="28" r="9"/>'
        if need in "SL":
            inner += '<text class="s-letter" x="44" y="46" text-anchor="middle">%s</text>' % need
        if hit:
            inner += '<text class="s-letter" x="44" y="12" text-anchor="middle">!</text>'
        out.append('<g class="%s" transform="translate(%d %d)">%s</g>' % (cls, x, y, inner))
    # placed pieces
    for (r, c), (piece, state) in sorted(placed.items()):
        out.append('<g class="ml-piece ml-piece-%s" data-piece="%s" transform="translate(%d %d)">%s</g>' % (piece, piece, PAD + c * U, PAD + r * U, glyph(piece, state)))
    # hit targets (the page puts its clicks and the keyboard cursor here)
    for r in range(board.h):
        for c in range(board.w):
            slot = "1" if (r, c) in board.slots else "0"
            out.append('<rect class="ml-hit" data-r="%d" data-c="%d" data-slot="%s" x="%d" y="%d" width="%d" height="%d"/>' % (r, c, slot, PAD + c * U, PAD + r * U, U, U))
    out.append("</svg>")
    return "".join(out)


# ---- the relay map ---------------------------------------------------------------------------------------------------------
NODE_W, NODE_GAP, MAP_LEFT, MAP_ROW = 38, 6, 8, 64


def map_svg(chapters):
    """`chapters` is the view's chapter list (each with `benches`). Cleared benches are filled nodes with a tick, a bench cleared with the
    fewest pieces has a second ring, an uncleared one is a dashed outline, and a chapter that is not open yet is drawn dim with the word Locked."""
    slots = max(len(ch["benches"]) for ch in chapters)
    width = MAP_LEFT * 2 + slots * NODE_W + (slots - 1) * NODE_GAP
    out = ['<svg class="ml-map" viewBox="0 0 %d %d" role="group" aria-label="Arden Relay map: %d chapters of benches">' % (width, MAP_ROW * len(chapters) + 8, len(chapters))]
    for row, ch in enumerate(chapters):
        y = 6 + row * MAP_ROW
        title = "%s  %d/%d" % (ch["name"], ch["cleared"], len(ch["benches"])) + ("" if ch["open"] else "  Locked")
        out.append('<text class="map-title%s" x="%d" y="%d">%s</text>' % ("" if ch["open"] else " locked", MAP_LEFT, y + 10, esc(title)))
        out.append('<line class="map-wire" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (MAP_LEFT + NODE_W // 2, y + 36, width - MAP_LEFT - NODE_W // 2, y + 36))
        for i, b in enumerate(ch["benches"]):
            cx = MAP_LEFT + i * (NODE_W + NODE_GAP) + NODE_W // 2
            cy = y + 36
            cls = "map-node " + ("cleared" if b["cleared"] else "empty") + (" fewest" if b["fewest"] else "") + (" current" if b["current"] else "") + ("" if ch["open"] else " locked")
            state = ", cleared with the fewest pieces" if b["fewest"] else (", cleared" if b["cleared"] else ", not cleared")
            label = "%s, chapter %d bench %d%s%s" % (b["name"], ch["number"], b["number"], state, "" if ch["open"] else ", locked until 5 benches of the chapter before are cleared")
            out.append('<g class="%s" data-id="%s" role="button" tabindex="0" aria-label="%s"%s>' % (cls, esc(b["id"]), esc(label), "" if ch["open"] else ' aria-disabled="true"'))
            out.append('<circle class="node" cx="%d" cy="%d" r="15"/>' % (cx, cy))
            if b["fewest"]:
                out.append('<circle class="node-ring" cx="%d" cy="%d" r="19"/>' % (cx, cy))
            if b["cleared"]:
                out.append('<path class="node-tick" d="M%d %d l4 4 l8 -9"/>' % (cx - 6, cy + 1))
            else:
                out.append('<text class="node-num" x="%d" y="%d" text-anchor="middle" dominant-baseline="central">%d</text>' % (cx, cy + 1, b["number"]))
            out.append("</g>")
    out.append("</svg>")
    return "".join(out)
