"""Lexis -- rung 2: the Compound language.

A sign here is built from COMPONENTS and every component means something. A glyph is two components in
fixed slots: a ROOT (what the thing is) then a SIZE (how big it is), so "ku" is root "k" with size "u".
The player can learn the parts and then read signs they have never been shown, which is the point of this
rung. The component codes are opaque letters on purpose (nothing in "k" hints at water); the view draws
each code as its own set of strokes (milestone 4).

Roots: k = water, m = grain, t = fire.     Sizes: o = small, u = big.

A message is one glyph: the station fetches that thing onto its tray. A glyph that is not root-then-size
is answered in-world, never as an error.
"""

from dataclasses import dataclass

COMPONENTS = {
    "k": ("water", "root"),
    "m": ("grain", "root"),
    "t": ("fire", "root"),
    "o": ("small", "size"),
    "u": ("big", "size"),
}
ROOTS = tuple(c for c, (_m, slot) in COMPONENTS.items() if slot == "root")
SIZES = tuple(c for c, (_m, slot) in COMPONENTS.items() if slot == "size")


class GlyphError(Exception):
    def __init__(self, reason, text):
        super().__init__(text)
        self.reason = reason
        self.text = text


@dataclass(frozen=True)
class Item:
    root: str    # meaning, e.g. "water"
    size: str    # "small" or "big"

    def label(self):
        return f"{self.size} {self.root}"


def read_glyph(glyph):
    """The Item a glyph names under the TRUE language, or GlyphError with an in-world line."""
    if not glyph:
        raise GlyphError("silence", "Nothing was sent. The tray stays as it is.")
    if any(c not in COMPONENTS for c in glyph):
        raise GlyphError("unknown_part", "Part of that sign is not one the station knows.")
    if len(glyph) != 2:
        raise GlyphError("shape", "A sign is two parts. This is not that shape.")
    first, second = glyph
    if COMPONENTS[first][1] != "root" or COMPONENTS[second][1] != "size":
        raise GlyphError("order", "The station reads the thing first and its size second. This sign is the other way round.")
    return Item(COMPONENTS[first][0], COMPONENTS[second][0])


@dataclass(frozen=True)
class Tray:
    items: tuple = ()

    def to_dict(self):
        return {"items": [i.label() for i in self.items]}


def describe_tray(tray):
    if not tray.items:
        return "The tray is empty."
    return "On the tray: " + ", ".join(i.label() for i in tray.items) + "."


@dataclass(frozen=True)
class Reaction:
    understood: bool
    tray: Tray
    text: str
    reason: str = ""


MAX_TRAY = 6


def react(glyph, tray):
    try:
        item = read_glyph(glyph)
    except GlyphError as err:
        return Reaction(False, tray, err.text, err.reason)
    items = (tray.items + (item,))[-MAX_TRAY:]
    after = Tray(items)
    return Reaction(True, after, describe_tray(after))


def all_valid_glyphs():
    return [r + s for r in ROOTS for s in SIZES]
