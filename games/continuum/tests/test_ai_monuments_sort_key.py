"""Tests for sort_key() in monuments.py."""

import monuments


def test_sort_key_orders_by_era_first():
    """Achievements from earlier eras should have a smaller sort key."""
    assert monuments.sort_key("reached_agrarian", 0) < monuments.sort_key("reached_classical", 0)


def test_sort_key_uses_catalog_index_within_same_era():
    """For the same era, a higher catalog index yields a larger sort key."""
    assert monuments.sort_key("reached_agrarian", 0) < monuments.sort_key("reached_agrarian", 1)


def test_sort_key_falls_back_to_star_for_unknown_ids():
    """Unknown achievement IDs fall back to 'star', placing them at the end of the era list."""
    star_index = monuments.KIND_ORDER.index("star")
    assert monuments.sort_key("unknown_achievement_id", 0) == (star_index, 0)
