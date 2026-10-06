"""Lexis -- rung 3: the Bridge language.

Planet 3 speaks in signs the player already knows how to read, plus a few new small signs that CHANGE
what a sentence means. Nouns are the Compound language's signs (root then size, planet 2). Numbers are the
Pulse language's numbers (planet 1, binary). The new part is three single-letter markers that follow a noun:

    p  plural: more than one. Followed by a Pulse number, how many (ku p 0011 is three big water)
    n  negation: none of that. The thing is taken away, all of it
    q  question: how many of that are there? The station answers, and changes nothing

A message is written as space-separated tokens, for example "ku", "ku p 0011", "ku n", "ku q". The marker
letters mean nothing in themselves (nothing about "p" says plural); the player works them out from scenes.

The world is a stock of things with counts (the counter on planet 2 grown up): a sentence adds, removes or
asks. Signals the language cannot say are answered in-world and change nothing.
"""

from dataclasses import dataclass

from compound import GlyphError, read_glyph
from pulse import PULSE

MARKERS = {"p": "plural", "n": "negate", "q": "ask"}
MAX_PER_ITEM = 7


@dataclass(frozen=True)
class Stock:
    items: tuple = ()      # ((label, count), ...) in the order things first arrived

    def count(self, label):
        return dict(self.items).get(label, 0)

    def with_count(self, label, count):
        count = max(0, min(count, MAX_PER_ITEM))
        rest = [(l, c) for l, c in self.items if l != label]
        if label in dict(self.items):
            rest = [(l, count if l == label else c) for l, c in self.items]
        elif count:
            rest.append((label, count))
        return Stock(tuple((l, c) for l, c in rest if c > 0))

    def to_dict(self):
        return {"items": [{"label": l, "count": c} for l, c in self.items]}


def describe_stock(stock):
    if not stock.items:
        return "The counter is empty."
    return "On the counter: " + ", ".join(f"{c} {l}" for l, c in stock.items) + "."


@dataclass(frozen=True)
class Reaction:
    understood: bool
    stock: Stock
    text: str
    reason: str = ""
    reply: str = ""      # what the station says when asked (empty otherwise)


def _noun(token):
    try:
        return read_glyph(token).label()
    except GlyphError:
        return None


def _is_number(token):
    return PULSE.is_number_token(token)


def react(message, stock):
    tokens = message.split()
    if not tokens:
        return Reaction(False, stock, "Nothing was sent. The counter stays as it is.", "silence")
    label = _noun(tokens[0])
    if label is None:
        return Reaction(False, stock, "The station does not recognise what you are talking about.", "no_thing")
    rest = tokens[1:]
    if not rest:
        after = stock.with_count(label, stock.count(label) + 1)
        return Reaction(True, after, describe_stock(after))
    marker = MARKERS.get(rest[0])
    if marker is None:
        return Reaction(False, stock, "The station knows the thing but not the small sign after it.", "unknown_marker")
    extra = rest[1:]
    if marker == "plural":
        if len(extra) != 1 or not _is_number(extra[0]):
            return Reaction(False, stock, "The station asks how many. It needs a count after that sign.", "plural_needs_count")
        n = PULSE.number_value(extra[0])
        after = stock.with_count(label, stock.count(label) + n)
        return Reaction(True, after, describe_stock(after))
    if extra:
        return Reaction(False, stock, "That sign stands alone after the thing. The station does not know what to do with the rest.", "extra")
    if marker == "negate":
        if stock.count(label) == 0:
            return Reaction(True, stock, f"There was no {label} to take away. " + describe_stock(stock))
        after = stock.with_count(label, 0)
        return Reaction(True, after, describe_stock(after))
    count = stock.count(label)
    reply = f"The station shows {count} {label}." if count else f"The station shows no {label}."
    return Reaction(True, stock, reply, "", reply)
