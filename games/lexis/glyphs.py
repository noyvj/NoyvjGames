"""Lexis -- drawing the Compound language's signs by code.

Every component is a small set of strokes in a 24 by 24 box, written as SVG path data, so the art is
generated from data (the project rule: no generated images) and a glyph is just its two components drawn
side by side. The shapes are deliberately abstract: no stroke resembles the thing it means, because
resemblance would hand the player the answer and the point of this rung is deduction.

`COMPONENT_PATHS` is what the view draws; the tests check every component has a path inside the box and that
no two components look alike.
"""

from compound import COMPONENTS

BOX = 24

COMPONENT_PATHS = {
    "k": "M3 8 L9 4 L9 12 L15 8 L15 16 L21 12",          # a zigzag
    "m": "M12 3 L12 21 M4 12 L20 12 M7 6 L17 18",          # a cross with one diagonal
    "t": "M18 4 C6 4 6 20 18 20",                          # an open curve
    "o": "M6 5 L6 11 M12 5 L12 11 M18 5 L18 11",           # three short ticks
    "u": "M4 18 L20 18 M12 4 L12 14 M9 21 L15 21",         # a long base with a stem
}


def glyph_paths(glyph):
    """The component paths of a glyph, in reading order, each with its box offset (0 for the first part)."""
    return [{"code": code, "d": COMPONENT_PATHS[code]} for code in glyph if code in COMPONENT_PATHS]


def covered_components():
    return set(COMPONENT_PATHS) == set(COMPONENTS)
