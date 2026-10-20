"""Tests for pack_ready() in charts.py."""


import charts


def test_pack_ready_returns_boolean_for_practice():
    """pack_ready('practice') returns a boolean indicating if the practice generator is loaded."""
    assert isinstance(charts.pack_ready(charts.PRACTICE_PACK), bool)


def test_pack_ready_returns_boolean_for_two_ships():
    """pack_ready('two-ships') returns a boolean indicating if gentwo is loaded."""
    assert isinstance(charts.pack_ready(charts.TWO_SHIPS_PACK), bool)


def test_pack_ready_returns_true_for_known_chapter_pack():
    """pack_ready for a known chapter pack returns True when the chapter is loaded (as it is in tests)."""
    # In the test environment, LAZY is False, so all chapters are pre-loaded.
    assert charts.pack_ready("chapter-wind") is True


def test_pack_ready_returns_false_for_unknown_pack():
    """pack_ready returns False for a pack ID that does not match any known pack or chapter."""
    assert charts.pack_ready("unknown-pack-xyz") is False
