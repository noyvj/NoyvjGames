"""Evidence Hunt -- code-drawn SVG: a low-poly house at night above each case, and a faceted emblem for each spirit kind. Strings only,
so the markup is unit-tested. Colours here are decoration: every state in the game is also written in words."""

import math

import lexicon as lx


def emblem(kind):
    """A 40x40 faceted gem for a spirit kind: a polygon with as many sides as the kind's emblem says, in the kind's hue."""
    sides, hue = lx.KIND_EMBLEM[kind]
    cx = cy = 20.0
    outer = []
    for i in range(sides):
        a = -math.pi / 2 + 2 * math.pi * i / sides
        outer.append((cx + 17 * math.cos(a), cy + 17 * math.sin(a)))
    pts = " ".join("%.1f,%.1f" % p for p in outer)
    parts = ['<svg class="emblem" viewBox="0 0 40 40" role="img" aria-label="%s emblem" xmlns="http://www.w3.org/2000/svg">' % lx.KIND_NAME[kind],
             '<polygon points="%s" fill="hsl(%d, 40%%, 46%%)" stroke="#0d1117" stroke-width="1.5"/>' % (pts, hue)]
    for i in range(sides):
        a, b = outer[i], outer[(i + 1) % sides]
        shade = 62 if i % 2 == 0 else 30
        parts.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="hsl(%d, 40%%, %d%%)" opacity="0.6"/>' % (cx, cy, a[0], a[1], b[0], b[1], hue, shade))
    parts.append('<polygon points="%s" fill="none" stroke="#0d1117" stroke-width="1.5"/>' % pts)
    parts.append("</svg>")
    return "".join(parts)


def scene(windows=3):
    """The strip above each case: a dark house against the night, a few windows lit. `windows` (1-5) is how many are lit."""
    lit = max(1, min(5, windows))
    out = ['<svg class="scene" viewBox="0 0 600 90" role="img" aria-label="A house at night" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">',
           '<rect width="600" height="90" class="sc-sky"/>',
           '<polygon points="70,10 80,8 88,14 84,22 74,24 66,18" class="sc-moon"/>',
           '<circle cx="150" cy="16" r="1.4" class="sc-star"/><circle cx="260" cy="10" r="1.2" class="sc-star"/><circle cx="480" cy="18" r="1.6" class="sc-star"/>'
           '<circle cx="560" cy="9" r="1.1" class="sc-star"/><circle cx="400" cy="12" r="1.2" class="sc-star"/>',
           '<polygon points="170,40 300,10 430,40" class="sc-roof"/>',
           '<polygon points="180,40 420,40 420,78 180,78" class="sc-wall"/>',
           '<polygon points="272,22 300,12 328,22 328,34 272,34" class="sc-wall-top"/>']
    for i in range(5):
        x = 196 + i * 44
        cls = "sc-lamp" if i < lit else "sc-pane"
        out.append('<polygon points="%d,50 %d,50 %d,66 %d,66" class="%s"/>' % (x, x + 20, x + 20, x, cls))
    out.append('<polygon points="292,60 308,60 308,78 292,78" class="sc-door"/>')
    out.append('<polygon points="0,78 600,78 600,90 0,90" class="sc-ground"/>')
    out.append('<polygon points="120,78 134,46 148,78" class="sc-tree"/><polygon points="458,78 474,40 490,78" class="sc-tree"/>')
    out.append("</svg>")
    return "".join(out)
