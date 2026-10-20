"""Tests for banners.is_unlocked()."""

import banners


def test_is_unlocked_returns_true_when_achievement_is_earned():
    item = next(b for b in banners.BANNERS if b["id"] == "sheaf")
    assert banners.is_unlocked(item, ["reached_agrarian"], 0) is True


def test_is_unlocked_returns_true_when_rank_index_meets_requirement():
    item = next(b for b in banners.BANNERS if b["id"] == "chevron")
    assert banners.is_unlocked(item, [], 1) is True


def test_is_unlocked_returns_true_for_items_without_achievement_or_rank():
    item = next(b for b in banners.BANNERS if b["id"] == "plain")
    assert banners.is_unlocked(item, [], 0) is True
