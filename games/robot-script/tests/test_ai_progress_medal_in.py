import progress
import rooms


def test_medal_in_normal_gold_returns_three():
    """Normal difficulty with a cleared room at par steps should return gold (3)."""
    rid = "wake-up"
    par = rooms.BY_ID[rid].par
    best = {rid: {"n": par, "t": ""}}
    hbest = {}
    assert progress.medal_in(best, hbest, rid, "normal") == 3


def test_medal_in_normal_uncleared_returns_zero():
    """Normal difficulty with a room not in best should return 0."""
    rid = "wake-up"
    best = {}
    hbest = {}
    assert progress.medal_in(best, hbest, rid, "normal") == 0


def test_medal_in_hard_uncleared_returns_zero():
    """Hard difficulty with a room not in hbest should return 0 (edge case)."""
    rid = "wake-up"
    best = {}
    hbest = {}
    assert progress.medal_in(best, hbest, rid, "hard") == 0
