"""Rule Finder -- the wall map: six drawers of eight cubbies, drawn as an SVG string so its markup is unit-tested.

A cubby's state is told by shape as well as light: an empty one is a dashed outline with its number, a named one is solid with a
tick, and 3, 2 or 1 pips under it say gold, silver or bronze. The current case has a heavy outline. Clicking (or Enter on) a cubby
opens that case."""

CUBBY_W, CUBBY_H, GAP = 40, 26, 6
ROW_H = 50
LEFT = 6
SLOTS = 8
WIDTH = LEFT * 2 + SLOTS * CUBBY_W + (SLOTS - 1) * GAP
PIPS = {"gold": 3, "silver": 2, "bronze": 1}


def _esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def wall_svg(drawers):
    """`drawers` is the view's `cases` list (drawers with their cases)."""
    height = ROW_H * len(drawers) + 6
    out = ['<svg class="rf-wall" viewBox="0 0 %d %d" role="group" aria-label="The wall of drawers: %d drawers of %d cases">' % (WIDTH, height, len(drawers), SLOTS)]
    for r, d in enumerate(drawers):
        y = 4 + r * ROW_H
        out.append('<text class="wall-label" x="%d" y="%d">%s</text>' % (LEFT, y + 10, _esc("%s  %d/%d" % (d["name"], d["named"], d["total"]))))
        out.append('<polygon class="wall-rail" points="%d,%d %d,%d %d,%d %d,%d"/>' % (LEFT - 3, y + 16, WIDTH - LEFT + 3, y + 16, WIDTH - LEFT, y + 14, LEFT, y + 14))
        for i in range(SLOTS):
            x = LEFT + i * (CUBBY_W + GAP)
            if i >= len(d["cases"]):
                out.append('<rect class="cubby empty-slot" x="%d" y="%d" width="%d" height="%d" rx="4"/>' % (x, y + 18, CUBBY_W, CUBBY_H))
                continue
            c = d["cases"][i]
            cls = "rf-slot " + ("s1" if c["named"] else "s0") + (" current" if c["current"] else "")
            state = (", named, " + c["medal"] + " medal") if c["named"] else ", not named yet"
            label = "%s, %s, case %d of %d%s" % (c["name"], d["name"], c["number"], len(d["cases"]), state)
            out.append('<g class="%s" data-id="%s" role="button" tabindex="0" aria-label="%s">' % (cls, _esc(c["id"]), _esc(label)))
            out.append('<rect class="cubby" x="%d" y="%d" width="%d" height="%d" rx="4"/>' % (x, y + 18, CUBBY_W, CUBBY_H))
            out.append('<text class="cubby-num" x="%d" y="%d">%d</text>' % (x + 7, y + 36, c["number"]))
            if c["named"]:
                out.append('<path class="cubby-tick" d="M%d %d l4 4 l8 -9"/>' % (x + CUBBY_W - 18, y + 31))
                for p in range(PIPS.get(c["medal"], 1)):
                    out.append('<circle class="pip %s" cx="%d" cy="%d" r="2"/>' % (c["medal"], x + CUBBY_W // 2 - 6 + p * 6 - (PIPS.get(c["medal"], 1) - 1) * 3 + 3, y + 41))
            out.append("</g>")
    out.append("</svg>")
    return "".join(out)
