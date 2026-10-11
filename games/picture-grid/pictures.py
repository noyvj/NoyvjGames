"""Picture Grid -- the registry of galleries and pictures.

Each `pictures_gN.py` module is frozen, hand-authored data: a gallery description and its pictures as bitmaps ('#' filled, '.'
empty). This module wraps them, derives the clues (a pure function of the bitmap, so the stored picture and its clues can never
disagree) and answers the gating question. Nothing here reads a clock or a random source.

Gating: gallery 0 is open from the start; gallery n+1 opens once OPEN_AT pictures of gallery n are hung. Inside a gallery every
picture is open, in any order.
"""

import nonogram
import pictures_g1
import pictures_g2
import pictures_g3

OPEN_AT = 6                       # pictures hung in a gallery before the next one opens
TINTS = ("brass", "teal", "rose", "violet", "moss", "sky")      # the css has one three-tone ramp per name

_MODULES = (pictures_g1, pictures_g2, pictures_g3)


class Picture:
    def __init__(self, spec, gallery, number):
        self.id = spec["id"]
        self.title = spec["title"]
        self.caption = spec["caption"]
        self.tint = spec["tint"]
        self.rows = tuple(spec["rows"])
        self.height = len(self.rows)
        self.width = len(self.rows[0])
        row_clues, col_clues = nonogram.clues_of(self.rows)
        self.row_clues = row_clues
        self.col_clues = col_clues
        self.gallery = gallery              # index into GALLERIES
        self.number = number                # 1-based place inside its gallery

    @property
    def size(self):
        return "%dx%d" % (self.width, self.height)

    def solution_grid(self):
        return nonogram.grid_of(self.rows)


GALLERIES = []
ALL = []
BY_ID = {}
for _g, _mod in enumerate(_MODULES):
    _items = [Picture(spec, _g, i + 1) for i, spec in enumerate(_mod.PICTURES)]
    GALLERIES.append({"id": _mod.GALLERY["id"], "name": _mod.GALLERY["name"], "blurb": _mod.GALLERY["blurb"], "pictures": _items})
    for _p in _items:
        ALL.append(_p)
        BY_ID[_p.id] = _p
ORDER = [p.id for p in ALL]


def gallery_hung(solved, g):
    """How many pictures of gallery `g` are in the `solved` collection (ids)."""
    return sum(1 for p in GALLERIES[g]["pictures"] if p.id in solved)


def gallery_open(solved, g):
    """Is gallery `g` open given the hung pictures? Gallery 0 always; the next one once OPEN_AT of the one before are hung."""
    if g <= 0:
        return True
    if g >= len(GALLERIES):
        return False
    return gallery_open(solved, g - 1) and gallery_hung(solved, g - 1) >= min(OPEN_AT, len(GALLERIES[g - 1]["pictures"]))


def picture_open(solved, pid):
    p = BY_ID.get(pid)
    return p is not None and gallery_open(solved, p.gallery)


def galleries_done(solved):
    """Galleries with every picture hung."""
    return sum(1 for g in range(len(GALLERIES)) if gallery_hung(solved, g) == len(GALLERIES[g]["pictures"]))
