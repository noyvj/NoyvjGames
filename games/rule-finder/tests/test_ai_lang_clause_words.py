"""Tests for lang.clause_words."""

import lang


def test_clause_words_returns_yes_phrase_for_numbers():
    assert lang.clause_words(lang.NUM, "even") == "is even"


def test_clause_words_returns_yes_phrase_for_shapes_and_grids():
    assert lang.clause_words(lang.SHAPE, "has:c") == "has a circle in it"
    assert lang.clause_words(lang.GRID, "count_ge:2") == "has 2 or more filled squares"


def test_clause_words_returns_no_phrase_when_negated():
    assert lang.clause_words(lang.NUM, "even", neg=1) == "is odd"
