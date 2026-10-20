"""Edge-case tests for achievements.py."""


import achievements


def test_earned_with_empty_facts():
    """earned returns an empty list when facts are missing."""
    assert achievements.earned({}) == []


def test_earned_with_zero_values():
    """earned ignores facts that are exactly zero when need is at least 1."""
    facts = {fact: 0 for _i, _l, _d, fact, _n in achievements.ACHIEVEMENTS}
    assert achievements.earned(facts) == []


def test_earned_with_largest_allowed_values():
    """earned handles very large integers without error."""
    facts = {fact: 2**63 - 1 for _i, _l, _d, fact, _n in achievements.ACHIEVEMENTS}
    assert set(achievements.earned(facts)) == set(achievements.IDS)


def test_view_clamps_have_to_need():
    """view clamps have to need so it never exceeds the target."""
    facts = {fact: 10**9 for _i, _l, _d, fact, _n in achievements.ACHIEVEMENTS}
    result = achievements.view(facts)
    for entry in result:
        assert entry["have"] == entry["need"]


def test_goals_with_count_zero():
    """goals returns an empty list when count is zero."""
    assert achievements.goals({}, count=0) == []


def test_goals_with_count_one():
    """goals returns exactly one item when count is 1."""
    assert len(achievements.goals({}, count=1)) == 1
