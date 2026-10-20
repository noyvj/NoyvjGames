"""Edge-case tests for cases.py public API."""

import cases


def test_medal_for_returns_correct_medals_at_boundaries():
    """medal_for should return gold, silver, or bronze exactly at par and silver boundaries."""
    c = cases.ALL_CASES[0]
    assert cases.medal_for(c, 0) == "gold"
    assert cases.medal_for(c, c.par) == "gold"
    assert cases.medal_for(c, c.par + 1) == "silver"
    assert cases.medal_for(c, c.par + cases.SILVER_ALLOWANCE) == "silver"
    assert cases.medal_for(c, c.par + cases.SILVER_ALLOWANCE + 1) == "bronze"


def test_case_words_and_families_are_non_empty():
    """Case.words and Case.families should always return non-empty strings/lists."""
    for c in cases.ALL_CASES:
        words = c.words
        families = c.families
        assert isinstance(words, str) and len(words) > 0
        assert isinstance(families, list) and len(families) > 0
