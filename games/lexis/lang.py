"""Lexis -- language definitions.

A language here is DATA plus a few rules, never hand-written logic per language, so the later rungs of
the ladder (compound glyphs, the bridge language, and the Large-size extras) are new data and new rules
on the same shapes (planning/lexis-plan.md sections 6 and 6b).

The signal itself is a string of marks. In the Pulse language the marks are "0" and "1" (drawn by the
view as two kinds of pulse); later languages use other mark sets but are still strings the parser reads.

Nothing here knows about the DOM, the world, or what the player has guessed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    """One word of a language: a stable id, what it means (the gloss the player is trying to find), what
    kind of word it is, and the exact signal that spells it."""

    id: str
    meaning: str
    kind: str     # "noun", "state" or "frame"
    form: str     # the marks, e.g. "1000"


@dataclass(frozen=True)
class Language:
    """A language: token length, its words, and how its numbers are written.

    `number_rule` names the true rule; the hypotheses the player can wrongly believe live in deduce.py.
    Number tokens are not listed as words: a token whose first mark is `number_class_mark` spells a
    number in its remaining marks.
    """

    id: str
    name: str
    token_len: int
    words: tuple
    number_rule: str
    number_class_mark: str = "0"

    def by_form(self, form):
        for word in self.words:
            if word.form == form:
                return word
        return None

    def by_id(self, word_id):
        for word in self.words:
            if word.id == word_id:
                return word
        raise KeyError(word_id)

    def is_number_token(self, token):
        return len(token) == self.token_len and token[0] == self.number_class_mark

    def number_value(self, token):
        """The true value of a number token under this language's own rule."""
        return decode_number(token[1:], self.number_rule)


# --- number rules ----------------------------------------------------------------------------
# The true rule of the Pulse language is "binary_msb". The others exist so the deducibility checker can
# prove the scenes rule them out: a player who guesses "count the 1s" or "read it backwards" must be
# contradicted by evidence shown before they are asked to rely on the rule.

def decode_number(bits, rule):
    if rule == "binary_msb":
        return int(bits, 2)
    if rule == "binary_lsb":
        return int(bits[::-1], 2)
    if rule == "popcount":
        return bits.count("1")
    raise ValueError(f"unknown number rule {rule!r}")


NUMBER_RULES = ("binary_msb", "binary_lsb", "popcount")
