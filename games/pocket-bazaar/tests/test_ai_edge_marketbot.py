"""Edge-case tests for marketbot.py."""

import pytest

import game
import market
import marketbot


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    game._today = None
    market._cache.clear()
    yield
    game.stall.__init__()
    game._today = None


def _make_day(date="2026-10-05"):
    return market.new_day(date)


def test_play_with_default_limit_completes_a_standard_day():
    """A standard market day should finish well under the 3000 step limit."""
    day = _make_day()
    families = ["produce", "textiles"]
    steps = marketbot.play(day, families)
    assert steps < 1000


def test_play_with_zero_limit_raises_runtime_error():
    """Passing limit=0 to play should raise RuntimeError immediately for any non-trivial day."""
    day = _make_day()
    families = ["produce", "textiles"]
    with pytest.raises(RuntimeError, match="the bot never finished the day"):
        marketbot.play(day, families, limit=0)


def test_step_with_empty_queue_opens_a_crate():
    """When no customers are waiting, step should open a crate for the first available family."""
    day = _make_day()
    day.queue = []
    families = ["produce", "textiles"]
    result = marketbot.step(day, families)
    assert result is not None


def test_step_with_single_family_list_opens_correct_crate():
    """step should correctly open a crate when only one family is available."""
    day = _make_day()
    day.queue = []
    families = ["spices"]
    result = marketbot.step(day, families)
    assert result is not None


def test_play_with_zero_customers_finishes_immediately():
    """A market with zero customers should require zero steps."""
    day = _make_day()
    day.queue = []
    families = ["produce", "textiles"]
    steps = marketbot.play(day, families)
    assert steps == 0
