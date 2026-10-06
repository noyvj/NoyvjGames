"""Lexis -- the deducibility checker for the Compound language (same guarantee as deduce.py).

A reading assigns each of the five component letters one of five meanings (water, grain, fire, small, big; repeats allowed)
and says whether a glyph is read root-then-size or size-then-root. It is consistent with the scenes when
reading every shown glyph produces exactly the tray the world produced. The scenes settle the language when
every consistent reading agrees on EVERY glyph the language can form, including the ones never shown.
"""

import itertools
from dataclasses import dataclass

from compound import COMPONENTS, Item, Tray, all_valid_glyphs

MEANINGS = ("water", "grain", "fire", "small", "big")
SIZE_MEANINGS = ("small", "big")
ORDERS = ("root_first", "size_first")


@dataclass(frozen=True)
class Reading:
    order: str
    meanings: tuple   # ((letter, meaning), ...) in a fixed letter order

    def meaning_of(self, letter):
        return dict(self.meanings).get(letter)


def all_readings():
    letters = tuple(COMPONENTS)
    # Every assignment, repeats allowed: the player is never told that each meaning has exactly one
    # letter, so the checker must not assume it (that would let elimination settle a word that was
    # never actually shown).
    for order in ORDERS:
        for assignment in itertools.product(MEANINGS, repeat=len(letters)):
            yield Reading(order, tuple(zip(letters, assignment)))


def read(reading, glyph):
    """The Item this reading makes of `glyph`, or None when the reading cannot make an item of it."""
    if len(glyph) != 2:
        return None
    first, second = glyph
    a, b = reading.meaning_of(first), reading.meaning_of(second)
    root, size = (a, b) if reading.order == "root_first" else (b, a)
    if root in SIZE_MEANINGS or size not in SIZE_MEANINGS:
        return None
    return Item(root, size)


def predict(reading, glyph, tray):
    item = read(reading, glyph)
    return tray if item is None else Tray((tray.items + (item,))[-6:])


def consistent_readings(scenes):
    return [r for r in all_readings() if all(predict(r, s.glyph, s.before) == s.after for s in scenes)]


def disagreements(scenes):
    readings = consistent_readings(scenes)
    if not readings:
        return [("no reading fits these scenes", None)]
    out = []
    for glyph in all_valid_glyphs():
        if len({predict(r, glyph, Tray()) for r in readings}) > 1:
            out.append(glyph)
    return out


def determinate(scenes):
    return not disagreements(scenes)
