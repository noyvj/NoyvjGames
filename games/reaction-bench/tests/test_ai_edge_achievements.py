"""Edge-case tests for achievements.py."""


import achievements


def test_facts_of_with_all_empty_inputs():
    """facts_of should return zeros when shelf, found, hinted, and first are all empty or zero."""
    facts = achievements.facts_of({}, 0, {}, set())
    assert facts["shelved"] == 0
    assert facts["found"] == 0
    assert facts["first"] == 0
    assert facts["salts"] == 0
    assert facts["oxygen"] == 0
    assert facts["clean"] == 0
    for c in range(len(achievements.CHAPTER_SIZE)):
        assert facts[f"ch{c}"] == 0


def test_facts_of_with_large_found_value():
    """facts_of passes through the found value without clamping, even if it exceeds the bench size."""
    facts = achievements.facts_of({}, 100, {}, set())
    assert facts["found"] == 100


def test_earned_with_empty_facts():
    """earned should return an empty list when no facts are provided."""
    assert achievements.earned({}) == []


def test_earned_with_all_needs_met():
    """earned should return all achievement IDs when every fact exceeds its need."""
    all_met_facts = {fact: 100 for fact in achievements.FACTS}
    earned_ids = achievements.earned(all_met_facts)
    assert set(earned_ids) == set(achievements.IDS)


def test_view_with_empty_facts():
    """view should return achievements with have=0 and earned=False when facts are empty."""
    view_list = achievements.view({})
    for entry in view_list:
        assert entry["have"] == 0
        assert entry["earned"] is False
        assert entry["need"] > 0


def test_view_with_excessive_facts():
    """view should cap have at need when facts exceed the requirement."""
    huge_facts = {fact: 1000 for fact in achievements.FACTS}
    view_list = achievements.view(huge_facts)
    for entry in view_list:
        assert entry["have"] == entry["need"]
        assert entry["earned"] is True
