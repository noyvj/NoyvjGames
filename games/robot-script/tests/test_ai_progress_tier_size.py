"""Tests for progress.tier_size()."""

import progress


def test_normal_difficulty_returns_best_steps():
    best = {"wake-up": {"n": 5, "t": "F"}}
    assert progress.tier_size(best, {}, "wake-up", "normal") == 5


def test_easy_difficulty_returns_best_steps():
    best = {"wake-up": {"n": 7, "t": "F F"}}
    assert progress.tier_size(best, {}, "wake-up", "easy") == 7


def test_hard_difficulty_returns_hbest_steps():
    hbest = {"wake-up": 6}
    assert progress.tier_size({}, hbest, "wake-up", "hard") == 6


def test_unchieved_room_returns_none():
    best = {}
    hbest = {}
    assert progress.tier_size(best, hbest, "wake-up", "normal") is None
