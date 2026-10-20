"""Tests for Reading.meaning_of() in deduce_compound.py."""


from compound import COMPONENTS
from deduce_compound import Reading


def test_meaning_of_returns_correct_meaning_for_known_letters():
    # Build a reading using the actual game data so the format is correct.
    meanings = tuple((letter, meaning) for letter, (meaning, _) in COMPONENTS.items())
    r = Reading("root_first", meanings)
    assert r.meaning_of("k") == "water"
    assert r.meaning_of("u") == "big"


def test_meaning_of_returns_none_for_unknown_letter():
    # Edge case: querying a letter not present in the reading's meanings.
    meanings = (("k", "water"), ("o", "small"))
    r = Reading("root_first", meanings)
    assert r.meaning_of("z") is None
