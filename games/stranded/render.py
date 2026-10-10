"""Stranded -- code-drawn SVG: the comms-screen moonscape, low-poly portraits of Ines and Bit, and the small branch-map overview.
Strings only, so the markup is unit-tested. Colours are decoration: every state is also written in words on the page."""

STARS = ((22, 12), (58, 30), (96, 8), (140, 24), (188, 10), (236, 20), (280, 6), (330, 26), (372, 12), (40, 52), (120, 46), (250, 44), (350, 50))


def _poly(points, cls, extra=""):
    return '<polygon class="%s" points="%s"%s/>' % (cls, " ".join("%d,%d" % p for p in points), extra)


def scene(day, flags=(), scene_id=""):
    """A 400x120 moonscape. The sky, planet and ground are fixed; the camp changes with the story: Bit's lamp once awake, the
    storm haze on day 5, the relay beam once the relay is lit, and the lander lifting on the lander ending."""
    flags = set(flags)
    parts = ['<svg class="scene" viewBox="0 0 400 120" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Sparrow Relay on Orrin, day %d" xmlns="http://www.w3.org/2000/svg">' % day,
             '<rect class="sc-space" x="0" y="0" width="400" height="120"/>']
    for x, y in STARS:
        parts.append('<rect class="sc-star" x="%d" y="%d" width="2" height="2"/>' % (x, y))
    # the gas giant, faceted, with its ring
    parts.append(_poly([(300, 8), (338, 14), (356, 44), (340, 76), (300, 84), (264, 70), (252, 40), (268, 16)], "sc-giant"))
    parts.append(_poly([(300, 8), (338, 14), (356, 44), (300, 40)], "sc-giant-lit"))
    parts.append(_poly([(264, 70), (252, 40), (300, 40), (300, 84)], "sc-giant-dark"))
    parts.append('<polygon class="sc-ring" points="236,52 300,40 372,36 372,42 300,48 240,60"/>')
    # ground facets
    parts.append(_poly([(0, 84), (70, 70), (150, 80), (240, 68), (320, 78), (400, 66), (400, 120), (0, 120)], "sc-ground"))
    parts.append(_poly([(0, 84), (70, 70), (80, 120), (0, 120)], "sc-ground-dark"))
    parts.append(_poly([(150, 80), (240, 68), (260, 120), (170, 120)], "sc-ground-lit"))
    # the relay house
    parts.append(_poly([(120, 66), (170, 62), (176, 80), (118, 82)], "sc-hut"))
    parts.append(_poly([(120, 66), (140, 56), (170, 62)], "sc-hut-roof"))
    parts.append('<rect class="sc-window" x="142" y="68" width="8" height="6"/>')
    # the dish on its mast (a crooked mast after the storm if it was never secured)
    parts.append('<polygon class="sc-mast" points="196,80 199,52 202,80"/>')
    parts.append('<polygon class="sc-dish" points="188,50 210,44 206,56 192,58"/>')
    # Kestrel, the lander with a bad back
    parts.append(_poly([(40, 80), (50, 56), (74, 54), (84, 80)], "sc-lander"))
    parts.append(_poly([(50, 56), (62, 44), (74, 54)], "sc-lander-top"))
    parts.append('<polygon class="sc-leg" points="40,80 34,90 38,90 46,80"/><polygon class="sc-leg" points="84,80 92,90 88,90 78,80"/>')
    if "bit" in flags and "battery" not in flags:
        lamp = "sc-bit-lamp"
        parts.append(_poly([(224, 84), (228, 76), (240, 76), (244, 84)], "sc-bit"))
        parts.append('<circle class="%s" cx="234" cy="79" r="3"/>' % lamp)
    if day == 5 and "storm" not in flags:
        parts.append('<rect class="sc-dust" x="0" y="0" width="400" height="120"/>')
    if scene_id in ("e_lantern", "e_keeper", "e_pavel") or scene_id in ("r11a", "r10b"):
        parts.append('<polygon class="sc-beam" points="199,48 330,0 400,20 400,60"/>')
    if scene_id in ("e_straight", "e_bit", "e_half"):
        parts.append('<polygon class="sc-trail" points="62,40 50,10 74,10"/>')
    parts.append("</svg>")
    return "".join(parts)


def ines(mood="plain"):
    """A faceted portrait of Ines in her helmet with the visor up."""
    return ('<svg class="bust" viewBox="0 0 80 80" role="img" aria-label="Ines Varga" xmlns="http://www.w3.org/2000/svg">'
            '<polygon points="8,80 14,60 40,54 66,60 72,80" class="pt-suit"/>'
            '<polygon points="40,54 14,60 8,80 40,80" class="pt-suit-dark"/>'
            '<polygon points="10,40 14,14 40,4 66,14 70,40 62,50 18,50" class="pt-helmet"/>'
            '<polygon points="20,22 40,12 60,22 58,44 40,54 22,44" class="pt-face"/>'
            '<polygon points="40,12 20,22 22,44 40,34" class="pt-face-lit"/>'
            '<polygon points="22,44 40,34 40,54" class="pt-face-dark"/>'
            '<polygon points="30,29 36,29 36,33 30,33" class="pt-eye"/><polygon points="44,29 50,29 50,33 44,33" class="pt-eye"/>'
            '<polygon points="34,44 46,44 44,47 36,47" class="pt-mouth"/>'
            '<polygon points="20,22 22,12 40,6 58,12 60,22 40,16" class="pt-hair"/>'
            '</svg>')


def bit():
    """A faceted portrait of Bit, the small maintenance robot, with its cracked lamp."""
    return ('<svg class="bust" viewBox="0 0 80 80" role="img" aria-label="Bit, the small robot" xmlns="http://www.w3.org/2000/svg">'
            '<polygon points="16,70 20,34 60,34 64,70" class="pt-bot"/>'
            '<polygon points="20,34 16,70 40,70 40,34" class="pt-bot-dark"/>'
            '<polygon points="26,22 54,22 56,34 24,34" class="pt-bot-top"/>'
            '<circle cx="40" cy="48" r="9" class="pt-bot-eye"/>'
            '<polygon points="36,40 44,44 40,50 43,56" class="pt-crack"/>'
            '<rect x="18" y="68" width="44" height="6" class="pt-bot-dark"/>'
            '</svg>')


def map_svg(days):
    """A small overview of the branch map. days = list of {'day': n, 'nodes': [{'id', 'seen', 'current', 'end', 'tried', 'total'}]}.
    Nodes are dots in one column per day; solid = seen, hollow = not found yet, a ring marks where you are. Decoration only:
    the same information is written out in the list beside it."""
    width, height = 12 * 30 + 20, 150
    parts = ['<svg class="map-svg" viewBox="0 0 %d %d" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">' % (width, height)]
    for d in days:
        x = 20 + (d["day"] - 1) * 30
        parts.append('<text class="map-day" x="%d" y="12" text-anchor="middle">%d</text>' % (x, d["day"]))
        count = len(d["nodes"])
        for k, node in enumerate(d["nodes"]):
            y = 24 + (k + 0.5) * (118.0 / max(count, 1))
            cls = "map-node" + (" seen" if node["seen"] else "") + (" end" if node["end"] else "") + (" here" if node["current"] else "")
            if node.get("loose"):
                cls += " loose"
            parts.append('<circle class="%s" cx="%d" cy="%d" r="%d"/>' % (cls, x, y, 6 if node["end"] else 5))
    parts.append("</svg>")
    return "".join(parts)
