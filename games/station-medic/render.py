"""Station Medic -- code-drawn SVG: low-poly faceted busts of the crew and the infirmary strip. Strings only, so the markup is
unit-tested. Colours here are decoration: a patient's state is always also written in words on the card."""

import cast

# skin, hair, garment (each crew member keeps the same look everywhere)
LOOKS = {
    "maren": ("#b9805a", "#2b1d16", "#4f7d5b", "bun"),
    "dov": ("#d3a27c", "#6b6b70", "#9a6a2f", "cap"),
    "imre": ("#e0b894", "#7a4b2d", "#3f6a99", "short"),
    "nell": ("#8a5a3c", "#15110f", "#8a4f6e", "side"),
    "teo": ("#c78d66", "#c9c9c9", "#7b7f3b", "beanie"),
    "halloran": ("#a56f4a", "#1b1b1f", "#3d4756", "bald"),
    "yusra": ("#c9966f", "#241a30", "#5b4b8a", "band"),
    "kit": ("#e3c2a0", "#b2552d", "#2e7d7a", "spike"),
    "orla": ("#bd8760", "#d8d8dc", "#7a2e3a", "long"),
    "pell": ("#d9a98a", "#e9e4d4", "#6a5a44", "goggles"),
}


def _shade(hex_color, amount):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (max(0, min(255, int(v + amount))) for v in (r, g, b))
    return "#%02x%02x%02x" % (r, g, b)


def bust(crew, settled=False):
    """A 80x80 faceted head-and-shoulders portrait."""
    skin, hair, cloth, style = LOOKS[crew]
    parts = ['<svg class="bust" viewBox="0 0 80 80" role="img" aria-label="%s" xmlns="http://www.w3.org/2000/svg">' % cast.CREW_BY_ID[crew]["name"],
             '<polygon points="8,80 14,60 40,54 66,60 72,80" fill="%s" stroke="#0d1117" stroke-width="1.5"/>' % cloth,
             '<polygon points="40,54 14,60 8,80 40,80" fill="%s" opacity="0.35"/>' % _shade(cloth, -50),
             '<polygon points="32,50 48,50 46,60 40,64 34,60" fill="%s"/>' % _shade(skin, -25),
             '<polygon points="40,10 56,18 58,36 48,50 32,50 22,36 24,18" fill="%s" stroke="#0d1117" stroke-width="1.5"/>' % skin,
             '<polygon points="40,10 24,18 22,36 40,32" fill="%s" opacity="0.5"/>' % _shade(skin, 28),
             '<polygon points="40,32 22,36 32,50 40,50" fill="%s" opacity="0.4"/>' % _shade(skin, -35),
             '<polygon points="31,30 36,30 36,34 31,34" fill="#0d1117"/><polygon points="44,30 49,30 49,34 44,34" fill="#0d1117"/>']
    if style == "bun":
        parts.append('<polygon points="40,6 56,16 58,26 40,18 22,26 24,16" fill="%s"/><polygon points="34,2 46,2 48,10 32,10" fill="%s"/>' % (hair, hair))
    elif style == "cap":
        parts.append('<polygon points="22,22 40,6 58,22 62,26 18,26" fill="%s"/>' % hair)
    elif style == "short":
        parts.append('<polygon points="24,22 40,8 56,22 54,16 40,10 26,16" fill="%s"/>' % hair)
    elif style == "side":
        parts.append('<polygon points="22,36 20,18 40,8 60,18 56,26 40,18 26,28" fill="%s"/>' % hair)
    elif style == "beanie":
        parts.append('<polygon points="22,24 26,10 40,4 54,10 58,24" fill="%s"/><rect x="22" y="22" width="36" height="5" fill="%s"/>' % (_shade(cloth, 30), hair))
    elif style == "bald":
        parts.append('<polygon points="30,14 40,10 50,14 40,16" fill="%s" opacity="0.5"/>' % _shade(skin, 40))
    elif style == "band":
        parts.append('<polygon points="22,36 20,16 40,6 60,16 58,36 54,22 40,14 26,22" fill="%s"/><rect x="22" y="22" width="36" height="3" fill="%s"/>' % (hair, cloth))
    elif style == "spike":
        parts.append('<polygon points="22,22 24,6 32,14 40,2 48,14 56,6 58,22 40,14" fill="%s"/>' % hair)
    elif style == "long":
        parts.append('<polygon points="22,36 18,16 40,6 62,16 58,36 56,60 24,60" fill="%s" opacity="0.9"/>' % hair)
        parts.append('<polygon points="22,24 40,12 58,24 40,20" fill="%s"/>' % _shade(hair, 25))
    elif style == "goggles":
        parts.append('<polygon points="24,22 40,10 56,22 40,18" fill="%s"/><rect x="28" y="27" width="10" height="8" rx="2" fill="none" stroke="#0d1117" stroke-width="2"/><rect x="42" y="27" width="10" height="8" rx="2" fill="none" stroke="#0d1117" stroke-width="2"/>' % hair)
    if settled:
        parts.append('<circle cx="66" cy="14" r="11" fill="#151c26" stroke="#7dffb2" stroke-width="2.5"/><path d="M60 14 l4 4 l8 -8" fill="none" stroke="#7dffb2" stroke-width="3"/>')
    parts.append("</svg>")
    return "".join(parts)


def scene(beds=0):
    """The strip above the ward: a dark infirmary wall with a porthole, a lamp and a row of beds (and the cold room's pane)."""
    out = ['<svg class="scene" viewBox="0 0 600 90" role="img" aria-label="The infirmary at night" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">',
           '<rect width="600" height="90" class="sc-wall"/>',
           '<polygon points="0,66 600,66 600,90 0,90" class="sc-floor"/>',
           '<polygon points="40,10 90,10 104,28 104,50 90,66 40,66 26,50 26,28" class="sc-port"/>',
           '<polygon points="48,18 82,18 92,30 92,48 82,58 48,58 38,48 38,30" class="sc-space"/>',
           '<circle cx="58" cy="30" r="1.6" class="sc-star"/><circle cx="76" cy="44" r="1.2" class="sc-star"/><circle cx="66" cy="50" r="1" class="sc-star"/>',
           '<polygon points="300,8 312,8 318,22 294,22" class="sc-lamp"/><polygon points="296,22 316,22 340,66 272,66" class="sc-beam"/>']
    for i in range(4):
        x = 140 + i * 90
        out.append('<polygon points="%d,52 %d,46 %d,46 %d,52 %d,66 %d,66" class="sc-bed"/>' % (x, x + 8, x + 62, x + 70, x + 70, x))
    if beds:
        out.append('<polygon points="500,18 580,18 580,66 500,66" class="sc-pane"/><polygon points="504,22 576,22 576,62 504,62" class="sc-pane-in"/>')
    out.append("</svg>")
    return "".join(out)
