"""Tests for citizens.bonus_text()."""

import citizens


def test_bonus_text_returns_formatted_string_for_single_delta():
    """A single delta from ERA_TRADES should produce a non-empty string."""
    result = citizens.bonus_text({"food_yield_mult": 0.02})
    assert isinstance(result, str)
    assert len(result) > 0


def test_bonus_text_combines_multiple_deltas_into_one_string():
    """Multiple deltas should be combined into a single non-empty string."""
    deltas = {"food_yield_mult": 0.02, "knowledge_mult": 0.03}
    result = citizens.bonus_text(deltas)
    assert isinstance(result, str)
    assert len(result) > 0


def test_bonus_text_returns_empty_string_for_no_deltas():
    """An empty dict should yield an empty string."""
    result = citizens.bonus_text({})
    assert isinstance(result, str)
    assert result == ""
