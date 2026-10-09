"""Robot Script -- the room as an SVG string (and as words).

The page draws this once per room and then only moves the robot and toggles classes (see app.js), so every thing that
changes has an id:  rs-robot, rs-carry, rs-part-<i>, rs-fill-<i>, rs-lamp-<k>, and doors carry class rs-door with
data-sw=<k>. Nothing here uses colour alone: a part is a diamond, a socket a dashed frame, a switch a round plate with
its number, a door barred with the number of its switch, the exit a ringed pad with its own label. Colours come from
the page's CSS (classes only, no inline colours) so both themes work.
"""

import room as roomlib

T = 48          # tile size in SVG units
PAD = 6


def _poly(points, cls, extra=""):
    return '<polygon class="%s" points="%s"%s/>' % (cls, " ".join("%g,%g" % p for p in points), extra)


def _tile(x, y):
    px, py = x * T, y * T
    shade = "rs-t%d" % ((x + y) % 2)
    first = _poly([(px, py), (px + T, py), (px, py + T)], "rs-fa")
    second = _poly([(px + T, py), (px + T, py + T), (px, py + T)], "rs-fb")
    return '<g class="rs-tile %s">%s%s</g>' % (shade, first, second)


def _wall(x, y):
    px, py = x * T, y * T
    return ('<g class="rs-wall"><rect class="rs-wall-base" x="%d" y="%d" width="%d" height="%d"/>%s%s'
            '<path class="rs-wall-x" d="M%d,%d L%d,%d M%d,%d L%d,%d"/></g>' % (
                px, py, T, T,
                _poly([(px + 3, py + 3), (px + T - 3, py + 3), (px + 3, py + T - 3)], "rs-wall-l"),
                _poly([(px + T - 3, py + 3), (px + T - 3, py + T - 3), (px + 3, py + T - 3)], "rs-wall-r"),
                px + 10, py + 10, px + T - 10, py + T - 10, px + T - 10, py + 10, px + 10, py + T - 10))


def _octagon(cx, cy, r):
    k = r * 0.41421356
    return [(cx - k, cy - r), (cx + k, cy - r), (cx + r, cy - k), (cx + r, cy + k),
            (cx + k, cy + r), (cx - k, cy + r), (cx - r, cy + k), (cx - r, cy - k)]


def _exit(x, y):
    cx, cy = x * T + T / 2, y * T + T / 2
    return ('<g class="rs-exit">%s%s<text class="rs-label" x="%g" y="%g" text-anchor="middle">EXIT</text></g>' % (
        _poly(_octagon(cx, cy, 20), "rs-exit-ring"), _poly(_octagon(cx, cy, 12), "rs-exit-core"), cx, cy + 4))


def _diamond(cx, cy, r):
    return [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]


def _part(i, x, y):
    cx, cy = x * T + T / 2, y * T + T / 2
    return ('<g class="rs-part" id="rs-part-%d">%s%s</g>' % (
        i, _poly(_diamond(cx, cy, 14), "rs-part-body"), _poly([(cx, cy - 14), (cx + 14, cy), (cx, cy)], "rs-part-shine")))


def _socket(i, x, y):
    px, py = x * T, y * T
    cx, cy = px + T / 2, py + T / 2
    return ('<g class="rs-socket"><rect class="rs-socket-frame" x="%g" y="%g" width="%g" height="%g" rx="4"/>%s'
            '<g class="rs-fill" id="rs-fill-%d">%s</g></g>' % (
                px + 8, py + 8, T - 16, T - 16, _poly(_diamond(cx, cy, 8), "rs-socket-hole"), i,
                _poly(_diamond(cx, cy, 13), "rs-part-body")))


def _switch(sid, x, y):
    cx, cy = x * T + T / 2, y * T + T / 2
    return ('<g class="rs-switch" id="rs-lamp-%d"><circle class="rs-switch-plate" cx="%g" cy="%g" r="16"/>'
            '<circle class="rs-switch-lamp" cx="%g" cy="%g" r="5"/><text class="rs-label rs-num" x="%g" y="%g" text-anchor="middle">%d</text></g>' % (
                sid, cx, cy, cx, cy - 5, cx, cy + 10, sid + 1))


def _door(sid, x, y):
    px, py = x * T, y * T
    bars = "".join('<rect class="rs-door-bar" x="%g" y="%g" width="5" height="%g"/>' % (px + 8 + k * 11, py + 4, T - 8) for k in range(3))
    return ('<g class="rs-door" data-sw="%d"><rect class="rs-door-frame" x="%g" y="%g" width="%g" height="%g" rx="3"/>%s'
            '<text class="rs-label rs-door-num" x="%g" y="%g" text-anchor="middle">%s</text></g>' % (
                sid, px + 4, py + 4, T - 8, T - 8, bars, px + T / 2, py + T / 2 + 5, "ABC"[sid]))


def _robot(layout):
    x, y, d = layout.start
    return ('<g id="rs-robot" class="rs-robot" style="transform:translate(%gpx,%gpx) rotate(%ddeg)"><g class="rs-robot-body">%s%s%s%s%s</g></g>' % (
        x * T + T / 2, y * T + T / 2, d * 90, _poly(_octagon(0, 0, 17), "rs-robot-shell"),
        _poly([(-8, -4), (8, -4), (8, 6), (-8, 6)], "rs-robot-face"),
        _poly([(-5, -17), (5, -17), (0, -26)], "rs-robot-nose"),
        '<circle class="rs-robot-eye" cx="-4" cy="0" r="2"/><circle class="rs-robot-eye" cx="4" cy="0" r="2"/>',
        '<g id="rs-carry" class="rs-carry">' + _poly(_diamond(0, 22, 8), "rs-part-body") + '</g>'))


def room_svg(layout, label="The room"):
    """The whole room, drawn in its starting state. The robot is placed by app.js from the first frame."""
    w, h = layout.w * T, layout.h * T
    out = ['<svg class="rs-room" xmlns="http://www.w3.org/2000/svg" viewBox="%d %d %d %d" role="img" aria-label="%s" focusable="false">' % (
        -PAD, -PAD, w + 2 * PAD, h + 2 * PAD, label.replace('"', "&quot;")),
        '<rect class="rs-frame" x="%d" y="%d" width="%d" height="%d" rx="6"/>' % (-PAD, -PAD, w + 2 * PAD, h + 2 * PAD)]
    for y in range(layout.h):
        for x in range(layout.w):
            out.append(_wall(x, y) if (x, y) in layout.walls else _tile(x, y))
    for (x, y), sid in sorted(layout.door_at.items()):
        out.append(_door(sid, x, y))
    for (x, y) in layout.exits:
        out.append(_exit(x, y))
    for i, (x, y) in enumerate(layout.sockets):
        out.append(_socket(i, x, y))
    for (x, y), sid in sorted(layout.switch_at.items(), key=lambda kv: kv[1]):
        out.append(_switch(sid, x, y))
    for i, (x, y) in enumerate(layout.parts):
        out.append(_part(i, x, y))
    out.append(_robot(layout))
    out.append("</svg>")
    return "".join(out)


def describe(layout):
    """The room in words, for screen readers and the 'room in words' disclosure: one line per kind of thing."""
    x, y, d = layout.start
    lines = ["The room is %d columns wide and %d rows tall. Columns count from the left and rows from the top, starting at 1." % (layout.w, layout.h),
             "The robot starts in column %d, row %d, facing %s." % (x + 1, y + 1, roomlib.HEADING_NAMES[d])]

    def spots(items):
        return ", ".join("column %d row %d" % (px + 1, py + 1) for px, py in items)
    if layout.exits:
        lines.append("The exit pad is in " + spots(layout.exits) + ".")
    if layout.parts:
        lines.append(("A part lies in " if len(layout.parts) == 1 else "%d parts lie in " % len(layout.parts)) + spots(layout.parts) + ".")
    if layout.sockets:
        lines.append(("A socket is in " if len(layout.sockets) == 1 else "%d sockets are in " % len(layout.sockets)) + spots(layout.sockets) + ".")
    for (px, py), sid in sorted(layout.switch_at.items(), key=lambda kv: kv[1]):
        lines.append("Switch %d is in column %d row %d." % (sid + 1, px + 1, py + 1))
    for (px, py), sid in sorted(layout.door_at.items(), key=lambda kv: kv[1]):
        lines.append("Door %s, opened by switch %d, is in column %d row %d." % ("ABC"[sid], sid + 1, px + 1, py + 1))
    if layout.walls:
        lines.append("Walls fill %d of the %d tiles." % (len(layout.walls), layout.w * layout.h))
    rows = []
    for yy in range(layout.h):
        rows.append("Row %d: " % (yy + 1) + " ".join(_word(layout, xx, yy) for xx in range(layout.w)))
    return lines, rows


def _word(layout, x, y):
    pos = (x, y)
    if pos in layout.walls:
        return "wall"
    if pos in layout.door_at:
        return "door" + "ABC"[layout.door_at[pos]]
    if pos in layout.exits:
        return "exit"
    if pos in layout.sockets:
        return "socket"
    if pos in layout.switch_at:
        return "switch" + str(layout.switch_at[pos] + 1)
    if pos in layout.part_at:
        return "part"
    if pos == layout.start[:2]:
        return "robot"
    return "floor"
