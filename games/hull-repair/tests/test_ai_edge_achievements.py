import achievements


def test_earned_empty_facts():
    """earned returns an empty list when facts is empty."""
    assert achievements.earned({}) == []


def test_earned_zero_values():
    """earned returns an empty list when all fact values are zero."""
    facts = {fact: 0 for _i, _l, _d, fact, need in achievements.ACHIEVEMENTS}
    assert achievements.earned(facts) == []


def test_earned_huge_values():
    """earned correctly identifies all achievements when facts exceed needs."""
    facts = {fact: need + 100 for _i, _l, _d, fact, need in achievements.ACHIEVEMENTS}
    assert set(achievements.earned(facts)) == set(achievements.IDS)


def test_view_empty_facts():
    """view returns correct structure with have=0 and earned=False for empty facts."""
    rows = achievements.view({})
    assert len(rows) == 14
    for row in rows:
        assert row["have"] == 0
        assert not row["earned"]


def test_view_huge_values():
    """view clamps have to need when facts exceed needs."""
    facts = {fact: 9999 for _i, _l, _d, fact, need in achievements.ACHIEVEMENTS}
    rows = achievements.view(facts)
    for row in rows:
        assert row["have"] == row["need"]
        assert row["earned"]


def test_goals_zero_count():
    """goals returns an empty list when count is 0."""
    assert achievements.goals({}, count=0) == []


def test_goals_large_count():
    """goals returns all unearned achievements when count exceeds total."""
    rows = achievements.goals({}, count=100)
    assert len(rows) == 14
