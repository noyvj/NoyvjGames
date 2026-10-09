"""Robot Script -- Scrap, the salvage drone you rebuild, one part per room (40 parts in ten zones).

A part is found by clearing its room and its finish follows the medal on that room (bronze rusted, silver clean, gold
polished), so a better list upgrades the same part: there is nothing to grind and nothing is missable. Scrap's drawing
and the parts list are computed from `best` only. Scrap's lines are flavour: they sit behind the story toggle and nothing
needed to play is ever in them.
"""

import progress
import rooms

FINISH = {1: "rusted", 2: "clean", 3: "polished"}

# zone id, name, how many parts
ZONES = (
    ("treads", "Treads", 4), ("chassis", "Chassis", 6), ("arm_l", "Left arm", 4), ("arm_r", "Right arm", 4),
    ("head", "Head", 5), ("lens", "Lenses", 3), ("antenna", "Antenna", 3), ("lamp", "Lamp", 3),
    ("plating", "Plating", 5), ("voice", "Voice box", 3),
)

# One part per room, in room order (zone, name). 40 in all.
PARTS = (
    ("treads", "Left drive roller"), ("treads", "Right drive roller"), ("treads", "Track pin set"), ("treads", "Axle bearing"),
    ("chassis", "Frame spar"), ("chassis", "Battery cradle"), ("chassis", "Cooling fan"),
    ("chassis", "Wiring loom"), ("chassis", "Hip joint"), ("chassis", "Service plate"),
    ("arm_l", "Left shoulder servo"), ("arm_l", "Left elbow hinge"), ("arm_l", "Left wrist ring"), ("arm_l", "Left pincer"),
    ("arm_r", "Right shoulder servo"), ("arm_r", "Right elbow hinge"), ("arm_r", "Right wrist ring"), ("arm_r", "Right pincer"),
    ("head", "Neck bearing"), ("head", "Skull plate"), ("head", "Cheek vent"),
    ("lens", "Left lens"), ("lens", "Right lens"), ("lens", "Focus ring"),
    ("head", "Jaw hinge"), ("head", "Crest fin"),
    ("antenna", "Antenna mast"), ("antenna", "Signal coil"), ("antenna", "Tuning knob"),
    ("lamp", "Lamp housing"), ("lamp", "Bulb"), ("lamp", "Reflector"),
    ("plating", "Chest plate"), ("plating", "Shoulder plate"), ("plating", "Back plate"), ("plating", "Shin plate"),
    ("plating", "Hatch cover"),
    ("voice", "Speaker cone"), ("voice", "Voice chip"), ("voice", "Static filter"),
)

LINES = {
    3: ("Fewer steps than I would have used. I will not say so again.",
        "That is the short way. I had the long way ready.",
        "Neat. Do not let it go to your head, you do not have one that I can see.",
        "Gold. The deck is almost embarrassed to have been this easy.",
        "I would have done it differently. It would not have been better.",
        "Efficient. Somewhere a supervisor would have wept."),
    2: ("Good enough. The robot did not complain, and it does not complain.",
        "There is a shorter list in there somewhere. I am not telling you where.",
        "Clean, if not quick. Take the part.",
        "Silver. The kind of silver you find at the bottom of a drawer.",
        "It works. That is the whole review."),
    1: ("It works. I have seen worse. I have been worse.",
        "Rusty, but it is a clear. The part is rusty too.",
        "A long way round, and you arrived. That counts for something.",
        "Bronze. The deck did not ask how."),
}


def part_for(rid):
    return PARTS[rooms.ORDER.index(rid)] if rooms.ORDER.index(rid) < len(PARTS) else ("chassis", "Spare part")


def line_for(rid, medal):
    options = LINES[medal if medal in LINES else 1]
    return options[rooms.ORDER.index(rid) % len(options)]


def parts_view(best):
    out = []
    for rid in rooms.ORDER:
        zone, name = part_for(rid)
        medal = progress.medal_of(best, rid)
        out.append({"room": rid, "room_name": rooms.BY_ID[rid].name, "zone": zone, "name": name, "found": bool(medal),
                    "finish": FINISH.get(medal, "")})
    return out


def zones_view(parts):
    out = []
    for zid, name, need in ZONES:
        mine = [p for p in parts if p["zone"] == zid]
        have = [p for p in mine if p["found"]]
        order = ("rusted", "clean", "polished")
        finish = order[min(order.index(p["finish"]) for p in have)] if have else ""
        out.append({"id": zid, "name": name, "have": len(have), "need": len(mine), "finish": finish})
    return out


def _zone_art(zid):
    """The shapes of a zone as SVG, in a 160 x 200 frame."""
    if zid == "treads":
        return '<rect x="26" y="168" width="48" height="22" rx="10"/><rect x="86" y="168" width="48" height="22" rx="10"/><circle cx="50" cy="179" r="4"/><circle cx="110" cy="179" r="4"/>'
    if zid == "chassis":
        return '<polygon points="46,100 114,100 120,130 114,164 46,164 40,130"/><path d="M60,110 L100,110 M60,150 L100,150"/>'
    if zid == "arm_l":
        return '<polygon points="14,104 36,104 34,146 26,158 16,146"/><path d="M16,126 L34,126"/>'
    if zid == "arm_r":
        return '<polygon points="146,104 124,104 126,146 134,158 144,146"/><path d="M144,126 L126,126"/>'
    if zid == "head":
        return '<polygon points="56,40 104,40 118,54 118,78 104,92 56,92 42,78 42,54"/>'
    if zid == "lens":
        return '<circle cx="66" cy="64" r="9"/><circle cx="94" cy="64" r="9"/>'
    if zid == "antenna":
        return '<path d="M80,40 L80,16"/><circle cx="80" cy="12" r="5"/><path d="M70,24 L90,24"/>'
    if zid == "lamp":
        return '<polygon points="70,110 90,110 96,124 64,124"/>'
    if zid == "plating":
        return '<path d="M50,104 L110,104 M48,160 L112,160 M46,132 L114,132"/><rect x="66" y="136" width="28" height="14" rx="2"/>'
    return '<rect x="66" y="82" width="28" height="7" rx="2"/><path d="M70,85.5 L90,85.5"/>'


def svg(best):
    zones = zones_view(parts_view(best))
    out = ['<svg class="scrap" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 200" role="img" aria-label="%s" focusable="false">' % label(zones)]
    for z in zones:
        state = "none" if not z["have"] else ("full" if z["have"] == z["need"] else "some")
        cls = "scrap-zone zone-%s" % state + (" fin-%s" % z["finish"] if z["finish"] else "")
        out.append('<g class="%s" data-zone="%s">%s</g>' % (cls, z["id"], _zone_art(z["id"])))
    out.append("</svg>")
    return "".join(out)


def label(zones):
    have = sum(z["have"] for z in zones)
    return "Scrap, the salvage drone, with %d of %d parts back on." % (have, sum(z["need"] for z in zones))


def view(best):
    parts = parts_view(best)
    zones = zones_view(parts)
    return {"svg": svg(best), "parts": parts, "zones": zones, "found": sum(1 for p in parts if p["found"]), "total": len(parts),
            "polished": sum(1 for p in parts if p["finish"] == "polished")}
