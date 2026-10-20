import achievements


def test_earned_with_empty_facts():
    """earned should return an empty list when facts is empty."""
    assert achievements.earned({}) == []


def test_earned_with_zero_values():
    """earned should return an empty list when all fact values are zero."""
    facts = {fact: 0 for _, _, _, fact, _, _ in achievements.ACHIEVEMENTS}
    assert achievements.earned(facts) == []


def test_earned_with_all_max_values():
    """earned should return all achievement IDs when every fact meets or exceeds its need."""
    facts = {fact: need for _, _, _, fact, need, _ in achievements.ACHIEVEMENTS}
    assert achievements.earned(facts) == list(achievements.IDS)


def test_view_with_empty_facts():
    """view should return a list of dicts with have=0 and earned=False when facts is empty."""
    result = achievements.view({})
    for entry in result:
        assert entry["have"] == 0
        assert entry["earned"] is False


def test_view_clamps_large_values():
    """view should clamp fact values to the achievement's need using min()."""
    facts = {fact: 1000 for _, _, _, fact, need, _ in achievements.ACHIEVEMENTS}
    result = achievements.view(facts)
    for entry in result:
        assert entry["have"] == entry["need"]
        assert entry["earned"] is True


def test_goals_empty_facts_default_count():
    """goals should return up to 3 unearned, non-sandbox achievements when facts is empty."""
    result = achievements.goals({})
    assert len(result) == 3
    for entry in result:
        assert not entry["earned"]
        assert entry["gate"] != achievements.SANDBOX


def test_goals_count_zero():
    """goals should return an empty list when count is 0."""
    assert achievements.goals({}, count=0) == []


def test_goals_sandbox_gate_respected():
    """goals should exclude the sandbox-gated achievement unless sandbox=True."""
    # Make all non-sbx achievements earned so tinkerer is among the first unearned
    facts = {fact: need for _, _, _, fact, need, _ in achievements.ACHIEVEMENTS if fact != "sbx"}
    facts["sbx"] = 9  # Not earned yet

    result_no_sandbox = achievements.goals(facts, count=3, sandbox=False)
    result_with_sandbox = achievements.goals(facts, count=3, sandbox=True)

    tinkerer_ids_no = [a["id"] for a in result_no_sandbox]
    assert "tinkerer" not in tinkerer_ids_no

    tinkerer_ids_yes = [a["id"] for a in result_with_sandbox]
    assert "tinkerer" in tinkerer_ids_yes
