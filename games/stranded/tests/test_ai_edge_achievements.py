"""Edge-case tests for achievements.py."""

import achievements


def test_earned_empty_facts():
    """earned returns [] when facts is empty."""
    assert achievements.earned({}) == []


def test_earned_zero_values():
    """earned returns [] when all fact values are zero."""
    facts = {fact: 0 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    assert achievements.earned(facts) == []


def test_earned_large_values():
    """earned returns all achievement ids when facts exceed every need."""
    max_need = max(need for _, _, _, _, need in achievements.ACHIEVEMENTS)
    facts = {fact: max_need * 10 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    assert set(achievements.earned(facts)) == set(achievements.IDS)


def test_view_clamps_have_to_need():
    """view clamps have to need when facts exceed it."""
    huge = {fact: 1000 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    result = achievements.view(huge)
    for item in result:
        assert item["have"] == item["need"]
        assert item["earned"] is True


def test_goals_count_clamping():
    """goals returns [] for count=0 and all unearned for large count."""
    assert achievements.goals({}, count=0) == []
    assert len(achievements.goals({}, count=100)) == len(achievements.ACHIEVEMENTS)
