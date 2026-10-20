"""Tests for unease.odd_allowed()."""

import data
import unease


def test_odd_allowed_allows_regular_night():
    """Night 5 is past the first odd night, not a season start, and not a festival."""
    assert unease.odd_allowed(5) is True


def test_odd_allowed_blocks_first_season_night():
    """Night 11 is the first night of a season, so odd beats are blocked."""
    assert unease.odd_allowed(data.NIGHTS_PER_SEASON + 1) is False


def test_odd_allowed_blocks_festival_night():
    """Night 20 is the festival night, which blocks odd beats."""
    assert unease.odd_allowed(data.NIGHTS_PER_SEASON * 2) is False


def test_odd_allowed_edge_before_start():
    """Night 3 is before FIRST_ODD_NIGHT (4), so it is not allowed."""
    assert unease.odd_allowed(3) is False
