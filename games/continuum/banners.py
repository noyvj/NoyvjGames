"""Continuum -- K-20: cosmetic banners and skyline flourishes.

A banner is a small cloth with an emblem, and a flourish is a decoration drawn along the
skyline. Both are **cosmetic only**: they change no number and no rule. They unlock by
earning an achievement or by reaching a Dynasty rank (dynasty.py), and the one you pick is
shown in the settlement archive and on the shareable card.

The pictures are drawn here from plain shapes as small self-contained SVG strings (inline
colours, no CSS classes, no external references), so the same string can be put on the page
and drawn onto the card's canvas. Nothing is generated art and nothing depends on colour
alone: each banner and flourish has a name, and each emblem is a distinct shape.

Pure functions of plain data. The choice rides in `campaign.ui["banner"]`, validated by
`clean()` on every read, so a hand-edited save can only ever show something from the catalog.
"""

import monuments

KEY = "banner"

CLOTH_COLOUR = "#5a3d70"
INK_COLOUR = "#f6e6c8"
POLE_COLOUR = "#c9a45c"

# Each entry: id, label, how it unlocks. `achievement` is an achievement id; `rank` is a
# Dynasty rank index (0 = Founder). `emblem` is a monuments kind or one of the rank emblems.
BANNERS = (
    {"id": "plain", "label": "Plain Cloth", "emblem": "plain"},
    {"id": "cairn", "label": "Cairn Banner", "emblem": "tribal", "achievement": "thriving_once"},
    {"id": "sheaf", "label": "Wheat Sheaf", "emblem": "agrarian", "achievement": "reached_agrarian"},
    {"id": "columns", "label": "Civic Columns", "emblem": "classical", "achievement": "reached_classical"},
    {"id": "tower", "label": "Guild Tower", "emblem": "medieval", "achievement": "reached_medieval"},
    {"id": "chimney", "label": "Chimney Smoke", "emblem": "industrial", "achievement": "reached_industrial"},
    {"id": "antenna", "label": "Antenna Mast", "emblem": "digital", "achievement": "reached_digital"},
    {"id": "ring", "label": "Habitat Ring", "emblem": "space", "achievement": "reached_space"},
    {"id": "relay", "label": "Relay Chain", "emblem": "relay", "achievement": "reached_relay"},
    {"id": "phoenix", "label": "Phoenix Star", "emblem": "star", "achievement": "phoenix_settlement"},
    {"id": "chevron", "label": "Steward's Chevron", "emblem": "chevron", "rank": 1},
    {"id": "bars", "label": "Warden's Bars", "emblem": "bars", "rank": 2},
    {"id": "crown", "label": "Elder's Crown", "emblem": "crown", "rank": 3},
    {"id": "sun", "label": "Archon's Sun", "emblem": "sun", "rank": 4},
    {"id": "twin_stars", "label": "Dynast's Twin Stars", "emblem": "twin_stars", "rank": 5},
)

FLOURISHES = (
    {"id": "none", "label": "No flourish"},
    {"id": "pennants", "label": "Pennants", "rank": 1},
    {"id": "lanterns", "label": "Lanterns", "achievement": "community_specialist"},
    {"id": "smoke", "label": "Rising smoke", "achievement": "reached_industrial"},
    {"id": "stars", "label": "Night stars", "achievement": "reached_space"},
    {"id": "beacons", "label": "Beacon chain", "achievement": "well_supplied_holdings"},
    {"id": "aurora", "label": "Aurora arcs", "rank": 3},
)

BANNER_IDS = tuple(b["id"] for b in BANNERS)
FLOURISH_IDS = tuple(f["id"] for f in FLOURISHES)
_BANNER = {b["id"]: b for b in BANNERS}
_FLOURISH = {f["id"]: f for f in FLOURISHES}
DEFAULT_CHOICE = {"banner": "plain", "flourish": "none"}


# --- the saved choice -----------------------------------------------------------------------
def clean(raw):
    """{'banner': id, 'flourish': id}, falling back to the plain defaults."""
    out = dict(DEFAULT_CHOICE)
    if isinstance(raw, dict):
        banner, flourish = raw.get("banner"), raw.get("flourish")
        if isinstance(banner, str) and banner in _BANNER:
            out["banner"] = banner
        if isinstance(flourish, str) and flourish in _FLOURISH:
            out["flourish"] = flourish
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else dict(DEFAULT_CHOICE)


def put(ui, choice):
    choice = clean(choice)
    if choice == DEFAULT_CHOICE:
        ui.pop(KEY, None)
    else:
        ui[KEY] = choice
    return choice


# --- unlocking ------------------------------------------------------------------------------
def is_unlocked(item, earned_ids, rank_index):
    """True when `item` (a catalog entry) is available to someone with these achievements and rank."""
    if "achievement" in item:
        return item["achievement"] in earned_ids
    if "rank" in item:
        return rank_index >= item["rank"]
    return True


def unlocked_banners(earned_ids, rank_index):
    return [b["id"] for b in BANNERS if is_unlocked(b, set(earned_ids), rank_index)]


def unlocked_flourishes(earned_ids, rank_index):
    return [f["id"] for f in FLOURISHES if is_unlocked(f, set(earned_ids), rank_index)]


def unlock_text(item, achievement_names, rank_names):
    """'Earn the achievement "X"' / 'Reach Dynasty rank Y' / '' for always-available entries."""
    if "achievement" in item:
        name = achievement_names.get(item["achievement"], item["achievement"])
        return f'Earn the achievement "{name}".'
    if "rank" in item:
        index = min(max(item["rank"], 0), len(rank_names) - 1)
        return f"Reach Dynasty rank {rank_names[index]}."
    return ""


def label_of(banner_id):
    return _BANNER[banner_id]["label"] if banner_id in _BANNER else _BANNER["plain"]["label"]


def flourish_label_of(flourish_id):
    return _FLOURISH[flourish_id]["label"] if flourish_id in _FLOURISH else _FLOURISH["none"]["label"]


def choose(ui, banner_id, flourish_id, earned_ids, rank_index):
    """Sets the player's pick. Either id may be None to keep the current one. A choice that is
    not unlocked (or not in the catalog) is refused. Returns (ok, reason)."""
    current = get(ui)
    banner = current["banner"] if banner_id is None else banner_id
    flourish = current["flourish"] if flourish_id is None else flourish_id
    if banner not in _BANNER or flourish not in _FLOURISH:
        return False, "That is not a banner or flourish in the catalogue."
    if not is_unlocked(_BANNER[banner], set(earned_ids), rank_index):
        return False, "That banner is not unlocked yet."
    if not is_unlocked(_FLOURISH[flourish], set(earned_ids), rank_index):
        return False, "That flourish is not unlocked yet."
    put(ui, {"banner": banner, "flourish": flourish})
    return True, ""


def effective(ui, earned_ids, rank_index):
    """The choice to actually display: anything no longer unlocked falls back to the default."""
    choice = get(ui)
    earned = set(earned_ids)
    if not is_unlocked(_BANNER[choice["banner"]], earned, rank_index):
        choice["banner"] = "plain"
    if not is_unlocked(_FLOURISH[choice["flourish"]], earned, rank_index):
        choice["flourish"] = "none"
    return choice


# --- drawing --------------------------------------------------------------------------------
def _inline(shape):
    """A monuments shape with its CSS classes swapped for inline attributes."""
    return (
        shape.replace('class="m-fill"', f'fill="{INK_COLOUR}"')
        .replace('class="m-line"', f'fill="none" stroke="{INK_COLOUR}" stroke-width="2.4" stroke-linecap="round"')
    )


def _rank_emblem(kind):
    ink = f'fill="{INK_COLOUR}"'
    line = f'fill="none" stroke="{INK_COLOUR}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"'
    if kind == "chevron":
        return (
            f'<polyline points="8,28 24,16 40,28" {line}/><polyline points="8,41 24,29 40,41" {line}/>'
        )
    if kind == "bars":
        return (
            f'<rect x="8" y="14" width="32" height="6" {ink}/><rect x="8" y="26" width="32" height="6" {ink}/>'
            f'<rect x="8" y="38" width="32" height="6" {ink}/>'
        )
    if kind == "crown":
        return (
            f'<polygon points="8,40 8,18 17,28 24,12 31,28 40,18 40,40" {ink}/>'
            f'<rect x="8" y="42" width="32" height="5" {ink}/>'
        )
    if kind == "sun":
        rays = "".join(
            f'<line x1="{24 + 12 * c:.1f}" y1="{30 + 12 * s:.1f}" x2="{24 + 20 * c:.1f}" y2="{30 + 20 * s:.1f}" '
            f'stroke="{INK_COLOUR}" stroke-width="3" stroke-linecap="round"/>'
            for c, s in (
                (1, 0), (0.7071, 0.7071), (0, 1), (-0.7071, 0.7071),
                (-1, 0), (-0.7071, -0.7071), (0, -1), (0.7071, -0.7071),
            )
        )
        return f'<circle cx="24" cy="30" r="9" {ink}/>{rays}'
    if kind == "twin_stars":
        return (
            f'<polygon points="{monuments._star_points(15, 24, 11, 4.5)}" {ink}/>'
            f'<polygon points="{monuments._star_points(33, 38, 11, 4.5)}" {ink}/>'
        )
    return ""


def _emblem(kind):
    if kind in monuments._SHAPES:
        return _inline(monuments._SHAPES[kind])
    return _rank_emblem(kind)


def banner_svg(banner_id, width=60):
    """A standalone SVG string for a banner (a hanging cloth with a swallowtail and an emblem)."""
    banner = _BANNER.get(banner_id, _BANNER["plain"])
    height = round(width * 84 / 60)
    emblem = _emblem(banner["emblem"])
    cloth = f'<polygon points="7,10 53,10 53,74 30,63 7,74" fill="{CLOTH_COLOUR}" stroke="{POLE_COLOUR}" stroke-width="2"/>'
    inner = (
        f'<g transform="translate(12 16) scale(0.75)">{emblem}</g>' if emblem
        else f'<line x1="30" y1="22" x2="30" y2="54" stroke="{INK_COLOUR}" stroke-width="2" stroke-dasharray="3 3"/>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 84" width="{width}" height="{height}" '
        f'role="img" aria-label="{banner["label"]} banner">'
        f'<rect x="3" y="4" width="54" height="5" rx="2" fill="{POLE_COLOUR}"/>{cloth}{inner}</svg>'
    )


def _flourish_body(flourish_id):
    gold = POLE_COLOUR
    ink = INK_COLOUR
    if flourish_id == "pennants":
        flags = "".join(
            f'<line x1="{x}" y1="10" x2="{x}" y2="38" stroke="{gold}" stroke-width="2"/>'
            f'<polygon points="{x},10 {x + 16},16 {x},22" fill="{ink}"/>'
            for x in range(14, 300, 42)
        )
        return flags
    if flourish_id == "lanterns":
        return "".join(
            f'<line x1="{x}" y1="2" x2="{x}" y2="14" stroke="{gold}" stroke-width="1.5"/>'
            f'<rect x="{x - 5}" y="14" width="10" height="14" rx="3" fill="{ink}" stroke="{gold}" stroke-width="1.5"/>'
            for x in range(20, 300, 36)
        )
    if flourish_id == "smoke":
        return "".join(
            f'<path d="M{x} 38 C{x - 8} 28 {x + 8} 20 {x} 10 S{x + 6} 2 {x} 0" fill="none" stroke="{ink}" '
            f'stroke-width="3" stroke-linecap="round" opacity="0.85"/>'
            for x in (40, 130, 220)
        )
    if flourish_id == "stars":
        return "".join(
            f'<polygon points="{monuments._star_points(x, y, 6, 2.4)}" fill="{ink}"/>'
            for x, y in ((18, 12), (60, 26), (104, 8), (150, 22), (196, 10), (238, 28), (280, 14))
        )
    if flourish_id == "beacons":
        return "".join(
            f'<circle cx="{x}" cy="{y}" r="4" fill="{ink}" stroke="{gold}" stroke-width="1.5"/>'
            f'<line x1="{x}" y1="{y + 4}" x2="{x}" y2="38" stroke="{gold}" stroke-width="1.5"/>'
            for x, y in ((20, 20), (80, 12), (140, 6), (200, 12), (260, 20))
        )
    if flourish_id == "aurora":
        return "".join(
            f'<path d="M0 {y} Q75 {y - 22} 150 {y} T300 {y}" fill="none" stroke="{ink}" stroke-width="2.5" opacity="{o}"/>'
            for y, o in ((30, 0.9), (22, 0.65), (14, 0.4))
        )
    return ""


def flourish_svg(flourish_id, width=300):
    """A standalone SVG strip (300x40 viewBox) for a skyline flourish; '' for none/unknown."""
    if flourish_id not in _FLOURISH or flourish_id == "none":
        return ""
    height = round(width * 40 / 300)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 40" width="{width}" height="{height}" '
        f'role="img" aria-label="{_FLOURISH[flourish_id]["label"]} skyline flourish">{_flourish_body(flourish_id)}</svg>'
    )


def card_payload(choice):
    """The cosmetic fields the shareable card gets (SVG strings drawn onto its canvas)."""
    choice = clean(choice)
    return {
        "banner_label": label_of(choice["banner"]),
        "banner_svg": banner_svg(choice["banner"], 120) if choice["banner"] != "plain" else "",
        "flourish_label": flourish_label_of(choice["flourish"]),
        "flourish_svg": flourish_svg(choice["flourish"], 600),
    }
