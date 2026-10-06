"""Lexis -- the deducibility checker for the Bridge language (same guarantee as the other two).

The player is assumed to know nouns (planet 2) and numbers (planet 1); the unknowns are the three marker
letters and where a marker sits relative to its noun. A reading assigns each marker letter one of four
roles (plural, negate, ask, nothing; repeats allowed, since nobody told the player each role has one
letter) and an order (marker after its noun, or before it). It is consistent when it reproduces every
scene's counter AND what the station said. The scenes settle the language when every consistent reading
agrees on every sentence the language can form.
"""

import itertools
from dataclasses import dataclass

from bridge import MARKERS, MAX_PER_ITEM, Stock, describe_stock
from compound import GlyphError, all_valid_glyphs, read_glyph
from pulse import PULSE, spell_number

ROLES = ("plural", "negate", "ask", "nothing")
ORDERS = ("noun_first", "marker_first")
LETTERS = tuple(MARKERS)


@dataclass(frozen=True)
class Reading:
    order: str
    roles: tuple    # ((letter, role), ...)

    def role_of(self, letter):
        return dict(self.roles).get(letter)


def all_readings():
    for order in ORDERS:
        for assignment in itertools.product(ROLES, repeat=len(LETTERS)):
            yield Reading(order, tuple(zip(LETTERS, assignment)))


def _noun(token):
    try:
        return read_glyph(token).label()
    except GlyphError:
        return None


def evaluate(reading, message, stock):
    """(stock, reply) this reading makes of `message`. A reading never errors: what it cannot place it ignores."""
    tokens = message.split()
    reply = ""
    i = 0
    pending_marker = None
    while i < len(tokens):
        token = tokens[i]
        label = _noun(token)
        role = reading.role_of(token) if token in MARKERS else None
        if label is not None:
            marker, step = None, 1
            if reading.order == "noun_first":
                if i + 1 < len(tokens) and tokens[i + 1] in MARKERS:
                    marker, step = reading.role_of(tokens[i + 1]), 2
            else:
                marker = pending_marker
            pending_marker = None
            number = None
            if marker == "plural":
                at = i + step
                if at < len(tokens) and PULSE.is_number_token(tokens[at]):
                    number, step = PULSE.number_value(tokens[at]), step + 1
            if marker == "plural" and number is not None:
                stock = stock.with_count(label, stock.count(label) + number)
            elif marker == "negate":
                stock = stock.with_count(label, 0)
            elif marker == "ask":
                count = stock.count(label)
                reply = f"The station shows {count} {label}." if count else f"The station shows no {label}."
            else:
                stock = stock.with_count(label, stock.count(label) + 1)
            i += step
        else:
            pending_marker = role if reading.order == "marker_first" and token in MARKERS else None
            i += 1
    return stock, reply


def _scene_matches(reading, scene):
    got, reply = evaluate(reading, scene.message, scene.before)
    return got == scene.after and reply == scene.reply


def consistent_readings(scenes):
    return [r for r in all_readings() if all(_scene_matches(r, s) for s in scenes)]


def _probe_messages():
    nouns = all_valid_glyphs()
    out = list(nouns)
    for noun in nouns:
        out += [f"{noun} p {spell_number(3)}", f"{noun} n", f"{noun} q"]
    return out


def disagreements(scenes):
    readings = consistent_readings(scenes)
    if not readings:
        return [("no reading fits these scenes", None)]
    start = Stock((("big water", 2), ("small grain", 1)))
    bad = []
    for message in _probe_messages():
        if len({evaluate(r, message, start) for r in readings}) > 1:
            bad.append(message)
    return bad


def determinate(scenes):
    return not disagreements(scenes)
