"""Hull Repair -- the board as an SVG string (and as words).

The page draws the board once per board (`board_svg`) and then replaces only the lines layer (`lines_svg`, inside
<g id="hr-lines">) as the player draws, so everything that moves lives in that one group. Nothing here uses colour
alone: each line has its own port shape (circle, square, triangle, diamond, hexagon, pentagon, cross, star) and its
letter, a source port is solid and a sink port is ringed, a hole is jagged and cracked, a bridge is a raised plate with
crossing rails, a valve carries an arrow, a mixer is a six-sided hub with an M. Colours come from the page's CSS (classes
only, no inline colours) so both themes work.
"""

import math

import rules

T = 48          # cell size in SVG units
PAD = 6
DASHES = {"A": "", "B": "2 6", "C": "7 5", "D": "1 5", "E": "9 3 2 3", "F": "3 3", "G": "12 4", "H": "1 8"}


def view_box(board):
    return "%d %d %d %d" % (-PAD, -PAD, board.w * T + 2 * PAD, board.h * T + 2 * PAD)


def _pts(points):
    return " ".join("%g,%g" % (round(x, 2), round(y, 2)) for x, y in points)


def _poly(points, cls, extra=""):
    return '<polygon class="%s" points="%s"%s/>' % (cls, _pts(points), extra)


def _regular(cx, cy, r, n, rot=-90):
    return [(cx + r * math.cos(math.radians(rot + 360.0 * i / n)), cy + r * math.sin(math.radians(rot + 360.0 * i / n))) for i in range(n)]


def _shape(name, cx, cy, r, cls):
    if name == "circle":
        return '<circle class="%s" cx="%g" cy="%g" r="%g"/>' % (cls, cx, cy, r)
    if name == "square":
        return '<rect class="%s" x="%g" y="%g" width="%g" height="%g" rx="2"/>' % (cls, cx - r * 0.85, cy - r * 0.85, r * 1.7, r * 1.7)
    if name == "triangle":
        return _poly(_regular(cx, cy + 1.5, r * 1.1, 3), cls)
    if name == "diamond":
        return _poly([(cx, cy - r * 1.1), (cx + r * 1.1, cy), (cx, cy + r * 1.1), (cx - r * 1.1, cy)], cls)
    if name == "hexagon":
        return _poly(_regular(cx, cy, r * 1.05, 6, 0), cls)
    if name == "pentagon":
        return _poly(_regular(cx, cy + 1, r * 1.05, 5), cls)
    if name == "cross":
        a, b = r * 1.05, r * 0.4
        return _poly([(cx - b, cy - a), (cx + b, cy - a), (cx + b, cy - b), (cx + a, cy - b), (cx + a, cy + b), (cx + b, cy + b),
                      (cx + b, cy + a), (cx - b, cy + a), (cx - b, cy + b), (cx - a, cy + b), (cx - a, cy - b), (cx - b, cy - b)], cls)
    outer, inner = r * 1.15, r * 0.5
    return _poly([(cx + (outer if i % 2 == 0 else inner) * math.cos(math.radians(-90 + 36 * i)),
                   cy + (outer if i % 2 == 0 else inner) * math.sin(math.radians(-90 + 36 * i))) for i in range(10)], cls)


def _center(cell):
    return cell[0] * T + T / 2, cell[1] * T + T / 2


def _tile(x, y):
    px, py = x * T, y * T
    shade = "hr-t%d" % ((x + y) % 2)
    return '<g class="hr-tile %s">%s%s</g>' % (shade, _poly([(px, py), (px + T, py), (px, py + T)], "hr-fa"),
                                               _poly([(px + T, py), (px + T, py + T), (px, py + T)], "hr-fb"))


def _hole(x, y):
    px, py = x * T, y * T
    jag = [(px + 2, py + 6), (px + 14, py + 1), (px + 24, py + 7), (px + 36, py + 2), (px + T - 2, py + 10), (px + T - 7, py + 22),
           (px + T - 1, py + 34), (px + T - 12, py + T - 3), (px + 26, py + T - 8), (px + 12, py + T - 1), (px + 3, py + T - 12), (px + 8, py + 24)]
    return ('<g class="hr-hole">%s<path class="hr-crack" d="M%g,%g L%g,%g L%g,%g M%g,%g L%g,%g"/></g>' % (
        _poly(jag, "hr-hole-body"), px + 14, py + 14, px + 24, py + 26, px + 20, py + 38, px + 24, py + 26, px + 38, py + 22))


def _bridge(x, y):
    px, py = x * T, y * T
    cx, cy = _center((x, y))
    return ('<g class="hr-bridge"><rect class="hr-bridge-plate" x="%g" y="%g" width="%g" height="%g" rx="3"/>'
            '<path class="hr-bridge-rail" d="M%g,%g H%g M%g,%g H%g"/><path class="hr-bridge-rail hr-bridge-over" d="M%g,%g V%g M%g,%g V%g"/></g>' % (
                px + 3, py + 3, T - 6, T - 6, px + 3, cy - 7, px + T - 3, px + 3, cy + 7, px + T - 3,
                cx - 7, py + 3, py + T - 3, cx + 7, py + 3, py + T - 3))


def _valve(x, y, d):
    cx, cy = _center((x, y))
    # an arrow pointing in direction d, drawn pointing up then rotated
    arrow = [(0, -17), (13, -2), (6, -2), (6, 14), (-6, 14), (-6, -2), (-13, -2)]
    return ('<g class="hr-valve"><rect class="hr-valve-plate" x="%g" y="%g" width="%g" height="%g" rx="5"/>'
            '<g transform="translate(%g %g) rotate(%d)">%s</g></g>' % (cx - 19, cy - 19, 38, 38, cx, cy, d * 90, _poly(arrow, "hr-valve-arrow")))


def _mixer(cell, pair):
    """A six-sided hub: the left half in the first line's colour, the right half in the second's, an M between."""
    cx, cy = _center(cell)
    hexa = _regular(cx, cy, 21, 6, 0)               # right, lower right, lower left, left, upper left, upper right
    right = [(cx, cy - 21 * math.sin(math.radians(60))), hexa[0], hexa[1], (cx, cy + 21 * math.sin(math.radians(60)))]
    left = [(cx, cy - 21 * math.sin(math.radians(60))), hexa[4], hexa[3], hexa[2], (cx, cy + 21 * math.sin(math.radians(60)))]
    right = [hexa[5], hexa[0], hexa[1], (cx, cy + 21 * math.sin(math.radians(60))), (cx, cy - 21 * math.sin(math.radians(60)))]
    return ('<g class="hr-mixer"><title>Mixer: %s and %s both end here</title>%s%s%s'
            '<text class="hr-label hr-mix-m" x="%g" y="%g" text-anchor="middle">M</text></g>' % (
                rules.LINE_NAMES[pair[0]], rules.LINE_NAMES[pair[1]], _poly(hexa, "hr-mixer-body"),
                _poly(left, "hr-mixer-half hr-c-" + pair[0]), _poly(right, "hr-mixer-half hr-c-" + pair[1]), cx, cy + 5))


def _port(board, cell, c, role):
    cx, cy = _center(cell)
    shape = rules.LINE_SHAPES[c]
    label = "%s %s port" % (rules.LINE_NAMES[c], "source" if role == "src" else "sink")
    return ('<g class="hr-port hr-%s hr-c-%s"><title>%s</title>%s<text class="hr-label hr-port-letter" x="%g" y="%g" text-anchor="middle">%s</text></g>' % (
        role, c, label, _shape(shape, cx, cy, 15, "hr-shape"), cx, cy + 5, c))


def board_svg(board, label=""):
    """The whole board, empty of lines. Lines go in <g id="hr-lines"> (see lines_svg)."""
    w, h = board.w * T, board.h * T
    out = ['<svg class="hr-board" xmlns="http://www.w3.org/2000/svg" viewBox="%s" role="img" aria-label="%s" focusable="false">' % (
        view_box(board), (label or "%s, %d by %d cells" % (board.name, board.w, board.h)).replace('"', "&quot;")),
        '<rect class="hr-frame" x="%d" y="%d" width="%d" height="%d" rx="6"/>' % (-PAD, -PAD, w + 2 * PAD, h + 2 * PAD)]
    for y in range(board.h):
        for x in range(board.w):
            out.append(_hole(x, y) if (x, y) in board.holes else _tile(x, y))
    for cell in sorted(board.bridges, key=lambda p: (p[1], p[0])):
        out.append(_bridge(*cell))
    for cell, d in sorted(board.valves.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        out.append(_valve(cell[0], cell[1], d))
    out.append('<g id="hr-lines"></g>')
    for cell, pair in sorted(board.mixers.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        out.append(_mixer(cell, pair))
    for c in board.lines:
        out.append(_port(board, board.src[c], c, "src"))
        if board.dst[c] not in board.mixers:
            out.append(_port(board, board.dst[c], c, "dst"))
    out.append('<rect id="hr-cursor" class="hr-cursor" x="0" y="0" width="%d" height="%d" rx="4" hidden="hidden"/>' % (T, T))
    out.append("</svg>")
    return "".join(out)


# ---- the lines layer -------------------------------------------------------------------------------------------------
def lines_svg(board, paths, ghosts=None, dots=True):
    """The lines layer: a dot on every open cell no line touches, ghost lines (a hint), then the lines. A line drawn through
    a bridge in the up-and-down lane is drawn last with a dark edge so it reads as passing over the other."""
    out = []
    if dots:
        for cell in rules.uncovered(board, paths):
            cx, cy = _center(cell)
            out.append('<circle class="hr-dot" cx="%g" cy="%g" r="3"/>' % (cx, cy))
    for c in sorted(ghosts or {}):
        pts = " ".join("%g,%g" % _center(p) for p in ghosts[c])
        out.append('<polyline class="hr-ghost hr-c-%s" points="%s"/>' % (c, pts))
    over = []
    for c in sorted(paths):
        path = [tuple(p) for p in paths[c]]
        if len(path) < 2:
            continue
        joined = rules.is_connected(board, c, path)
        pts = " ".join("%g,%g" % _center(p) for p in path)
        dash = DASHES.get(c, "")
        out.append('<g class="hr-line hr-c-%s%s" data-line="%s"><polyline class="hr-pipe" points="%s"/><polyline class="hr-core" points="%s"%s/></g>' % (
            c, " hr-joined" if joined else "", c, pts, pts, ' stroke-dasharray="%s"' % dash if dash else ""))
        for i in range(1, len(path)):
            if path[i] in board.bridges and path[i - 1][0] == path[i][0]:
                over.append((c, path[i]))
        if not joined:
            hx, hy = _center(path[-1])
            out.append('<circle class="hr-head hr-c-%s" cx="%g" cy="%g" r="9"/>' % (c, hx, hy))
    for c, cell in over:
        cx, cy = _center(cell)
        out.append('<g class="hr-over hr-c-%s"><path class="hr-over-edge" d="M%g,%g V%g"/><path class="hr-over-pipe" d="M%g,%g V%g"/></g>' % (
            c, cx, cy - T / 2, cy + T / 2, cx, cy - T / 2, cy + T / 2))
    return "".join(out)


# ---- words -----------------------------------------------------------------------------------------------------------
def _where(cell):
    return "column %d, row %d" % (cell[0] + 1, cell[1] + 1)


ARROW_WORDS = ("up", "right", "down", "left")


def describe(board):
    """The board in words, one line per thing, for screen readers and the 'board in words' disclosure."""
    lines = []
    for c in board.lines:
        name = rules.LINE_NAMES[c]
        if board.dst[c] in board.mixers:
            lines.append("%s line (%s, letter %s): source at %s, ends in the mixer at %s." % (name, rules.LINE_SHAPES[c], c, _where(board.src[c]), _where(board.dst[c])))
        else:
            lines.append("%s line (%s, letter %s): source at %s, sink at %s." % (name, rules.LINE_SHAPES[c], c, _where(board.src[c]), _where(board.dst[c])))
    for cell in sorted(board.holes, key=lambda p: (p[1], p[0])):
        lines.append("Hole (no hull) at %s." % _where(cell))
    for cell in sorted(board.bridges, key=lambda p: (p[1], p[0])):
        lines.append("Bridge at %s: one line may cross straight over another." % _where(cell))
    for cell, d in sorted(board.valves.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append("Valve at %s: lines go through it %s only." % (_where(cell), ARROW_WORDS[d]))
    for cell, pair in sorted(board.mixers.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        lines.append("Mixer at %s: the %s and %s lines both end here." % (_where(cell), rules.LINE_NAMES[pair[0]].lower(), rules.LINE_NAMES[pair[1]].lower()))
    return lines


def cell_words(board, paths, cell):
    """What is on one cell, for the keyboard cursor's spoken description."""
    here = _where(cell)
    if cell not in board.playable:
        return "%s: a hole in the hull." % here
    on = [rules.LINE_NAMES[c] for c in sorted(paths) if cell in [tuple(p) for p in paths[c]]]
    info = board.port_at.get(cell)
    if info is not None:
        return "%s: %s %s port%s." % (here, rules.LINE_NAMES[info[0]], "source" if info[1] == "src" else "sink", "" if on else ", no line yet")
    if cell in board.mixers:
        return "%s: mixer for %s and %s." % (here, rules.LINE_NAMES[board.mixers[cell][0]], rules.LINE_NAMES[board.mixers[cell][1]])
    kind = "bridge" if cell in board.bridges else ("valve pointing %s" % ARROW_WORDS[board.valves[cell]] if cell in board.valves else "open cell")
    if on:
        return "%s: %s with the %s line%s." % (here, kind, " and ".join(on), "s" if len(on) > 1 else "")
    return "%s: %s, empty." % (here, kind)
