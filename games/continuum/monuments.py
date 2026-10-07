"""Continuum -- K-31: the "monument row" look for the achievements panel.

Each achievement stands on a small plinth with a drawn monument for its era
(a cairn for the Tribal era, a column front for the Classical era, a chimney
for the Industrial era, a ring and spire for the Space Age, and so on). The
pictures are inline SVG built here from a few plain shapes: no image files and
nothing generated.

The look never depends on colour alone. An earned monument is drawn solid and
carries the words "Earned"; one not yet earned is drawn as an outline on a
dashed plinth and carries "Not yet earned". Every picture is decoration
(`aria-hidden`), the card's text carries the meaning.

Pure functions only: `game.py` builds the cards, this module supplies the
kind, the order, the caption and the drawing.
"""

import math

import sim

# Which monument each achievement stands under. A kind is an era id, or "star"
# for an achievement that is not tied to one era. Every catalog id must be
# here (a test checks it), so a new achievement cannot silently lose its picture.
ACHIEVEMENT_KIND = {
    "reached_agrarian": "agrarian",
    "reached_classical": "classical",
    "reached_medieval": "medieval",
    "reached_industrial": "industrial",
    "reached_digital": "digital",
    "reached_space": "space",
    "reached_relay": "relay",
    "thriving_once": "star",
    "phoenix_settlement": "star",
    "provision_specialist": "agrarian",
    "community_specialist": "classical",
    "craft_specialist": "medieval",
    "root_and_branch": "star",
    "equity_champion": "star",
    "built_to_last": "medieval",
    "full_coordination": "classical",
    "nobody_exposed": "medieval",
    "well_designed_rings": "space",
    "well_supplied_holdings": "relay",
    "a_real_city": "industrial",
    "looking_back": "tribal",
    "par_seasons": "relay",
    "par_time": "relay",
}

KIND_ORDER = list(sim.ERA_ORDER) + ["star"]
KIND_CAPTION = {era: f"{sim.ERA_LABEL[era]}" for era in sim.ERA_ORDER}
KIND_CAPTION["star"] = "Any era"


def kind_of(achievement_id):
    """The monument kind for an achievement id (an unknown id gets the star)."""
    return ACHIEVEMENT_KIND.get(achievement_id, "star")


def caption(kind):
    return KIND_CAPTION.get(kind, KIND_CAPTION["star"])


def sort_key(achievement_id, catalog_index):
    """Era order first, the catalog's own order within an era."""
    kind = kind_of(achievement_id)
    return (KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER), catalog_index)


def _star_points(cx, cy, outer, inner):
    pts = []
    for i in range(10):
        radius = outer if i % 2 == 0 else inner
        angle = -math.pi / 2 + i * math.pi / 5
        pts.append(f"{cx + radius * math.cos(angle):.1f},{cy + radius * math.sin(angle):.1f}")
    return " ".join(pts)


# Shapes use `m-fill` (solid when earned, empty outline otherwise) or
# `m-line` (always a plain stroke). All are drawn in a 48 x 56 box.
_SHAPES = {
    "tribal": (
        '<ellipse class="m-fill" cx="24" cy="41" rx="14" ry="6"/>'
        '<ellipse class="m-fill" cx="24" cy="31" rx="10" ry="5"/>'
        '<ellipse class="m-fill" cx="24" cy="22" rx="6" ry="4"/>'
    ),
    "agrarian": (
        '<line class="m-line" x1="24" y1="46" x2="24" y2="16"/>'
        '<line class="m-line" x1="24" y1="46" x2="14" y2="22"/>'
        '<line class="m-line" x1="24" y1="46" x2="34" y2="22"/>'
        '<ellipse class="m-fill" cx="24" cy="12" rx="3" ry="6"/>'
        '<ellipse class="m-fill" cx="12" cy="18" rx="3" ry="6" transform="rotate(-25 12 18)"/>'
        '<ellipse class="m-fill" cx="36" cy="18" rx="3" ry="6" transform="rotate(25 36 18)"/>'
    ),
    "classical": (
        '<polygon class="m-fill" points="6,23 24,10 42,23"/>'
        '<rect class="m-fill" x="9" y="26" width="5" height="21"/>'
        '<rect class="m-fill" x="21.5" y="26" width="5" height="21"/>'
        '<rect class="m-fill" x="34" y="26" width="5" height="21"/>'
    ),
    "medieval": (
        '<rect class="m-fill" x="15" y="23" width="18" height="25"/>'
        '<rect class="m-fill" x="13" y="16" width="5" height="7"/>'
        '<rect class="m-fill" x="21.5" y="16" width="5" height="7"/>'
        '<rect class="m-fill" x="30" y="16" width="5" height="7"/>'
        '<path class="m-line" d="M21 48 V39 a3 3 0 0 1 6 0 V48"/>'
    ),
    "industrial": (
        '<polygon class="m-fill" points="19,48 21,14 29,14 31,48"/>'
        '<rect class="m-fill" x="5" y="36" width="12" height="12"/>'
        '<circle class="m-line" cx="33" cy="10" r="3"/>'
        '<circle class="m-line" cx="39" cy="6" r="2.5"/>'
    ),
    "digital": (
        '<polygon class="m-fill" points="18,48 24,14 30,48"/>'
        '<circle class="m-fill" cx="24" cy="11" r="3"/>'
        '<path class="m-line" d="M16 18 Q24 8 32 18"/>'
        '<path class="m-line" d="M11 23 Q24 3 37 23"/>'
    ),
    "space": (
        '<polygon class="m-fill" points="20,48 24,12 28,48"/>'
        '<ellipse class="m-line" cx="24" cy="32" rx="19" ry="7"/>'
        '<circle class="m-fill" cx="24" cy="10" r="2.5"/>'
    ),
    "relay": (
        '<circle class="m-fill" cx="11" cy="39" r="6"/>'
        '<circle class="m-fill" cx="37" cy="20" r="6"/>'
        '<path class="m-line" d="M16 35 Q24 27 32 24"/>'
        '<circle class="m-line" cx="22" cy="29" r="1.5"/>'
        '<circle class="m-line" cx="27" cy="26.5" r="1.5"/>'
    ),
    "star": '<polygon class="m-fill" points="' + _star_points(24, 29, 17, 7) + '"/>',
}


def icon_svg(kind, earned):
    """The monument's SVG markup (a plain string). Unknown kinds draw the star."""
    shape = _SHAPES.get(kind, _SHAPES["star"])
    state = "earned" if earned else "locked"
    return (
        f'<svg class="monument-svg monument-svg--{state}" viewBox="0 0 48 56" width="48" height="56" '
        f'aria-hidden="true" focusable="false">'
        f'{shape}<rect class="m-plinth" x="6" y="49" width="36" height="5" rx="1"/></svg>'
    )
