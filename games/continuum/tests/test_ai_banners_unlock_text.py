"""Tests for banners.unlock_text()."""

import banners


def test_unlock_text_returns_achievement_string():
    item = next(b for b in banners.BANNERS if b["id"] == "sheaf")
    achievement_names = {"reached_agrarian": "Reach Agrarian Era"}
    rank_names = ["Founder", "Steward"]
    assert banners.unlock_text(item, achievement_names, rank_names) == 'Earn the achievement "Reach Agrarian Era".'


def test_unlock_text_returns_rank_string():
    item = next(b for b in banners.BANNERS if b["id"] == "chevron")
    achievement_names = {}
    rank_names = ["Founder", "Steward", "Warden"]
    assert banners.unlock_text(item, achievement_names, rank_names) == "Reach Dynasty rank Steward."


def test_unlock_text_clamps_rank_index_to_bounds():
    item = {"id": "crown", "label": "Elder's Crown", "emblem": "crown", "rank": 10}
    achievement_names = {}
    rank_names = ["Founder", "Steward"]
    assert banners.unlock_text(item, achievement_names, rank_names) == "Reach Dynasty rank Steward."
