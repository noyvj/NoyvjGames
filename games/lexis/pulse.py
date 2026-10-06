"""Lexis -- rung 1: the Pulse language.

The earliest signals are bare: two marks, and meaning only from pattern and position. Every token is four
marks. If the first mark is "0" the token is a NUMBER and the other three marks spell it in binary,
most significant mark first (0011 is three). If the first mark is "1" the token is a WORD.

Words: lamp, door (things the station has), open, shut (what a door can be), and a frame word that ends
every sentence. Three word forms are unused on purpose: a sender that says something the language cannot
say is part of the world, and the parser must answer it in-world rather than crash.

Sentences: [lamp][number][end]  or  [door][open|shut][end].
"""

from lang import Language, Word

PULSE = Language(
    id="pulse",
    name="Pulse",
    token_len=4,
    number_rule="binary_msb",
    number_class_mark="0",
    words=(
        Word("lamp", "lamp", "noun", "1000"),
        Word("door", "door", "noun", "1001"),
        Word("open", "open", "state", "1010"),
        Word("shut", "shut", "state", "1011"),
        Word("end", "end of message", "frame", "1111"),
    ),
)

# The largest number a three-mark number can spell, and the most lamps the station has.
MAX_NUMBER = 7


def spell_number(n, language=PULSE):
    """The marks for number `n` (0..7): the way a sender, or the player's sentence builder, writes it."""
    if not 0 <= n <= MAX_NUMBER:
        raise ValueError(f"{n} cannot be spelled in three marks")
    return language.number_class_mark + format(n, "03b")


def say_lamps(n, language=PULSE):
    return language.by_id("lamp").form + spell_number(n, language) + language.by_id("end").form


def say_door(state_id, language=PULSE):
    if state_id not in ("open", "shut"):
        raise ValueError(state_id)
    return language.by_id("door").form + language.by_id(state_id).form + language.by_id("end").form
