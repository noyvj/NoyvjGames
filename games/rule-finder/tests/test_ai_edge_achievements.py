"""Edge-case tests for achievements.py."""

import achievements


def test_earned_with_empty_facts_returns_no_ids():
    assert achievements.earned({}) == []


def test_earned_with_zero_values_returns_no_ids():
    facts = {fact: 0 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    assert achievements.earned(facts) == []


def test_view_clamps_have_to_need_when_facts_exceed_it():
    facts = {fact: 1000 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    result = achievements.view(facts)
    for entry in result:
        assert entry["have"] == entry["need"]
        assert entry["earned"] is True


def test_goals_with_zero_count_returns_empty_list():
    assert achievements.goals({}, count=0) == []


def test_goals_with_all_earned_returns_empty_list():
    facts = {fact: 1000 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    assert achievements.goals(facts, count=3) == []


def test_goals_with_large_count_returns_all_unearned():
    facts = {fact: 0 for _, _, _, fact, _ in achievements.ACHIEVEMENTS}
    unearned_count = len(achievements.ACHIEVEMENTS)
    assert len(achievements.goals(facts, count=unearned_count + 10)) == unearned_count
