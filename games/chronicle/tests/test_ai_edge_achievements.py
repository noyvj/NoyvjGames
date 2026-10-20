"""Edge-case tests for achievements.py."""

import achievements


def test_earned_empty_state_and_sets():
    """Empty state and sets should yield no achievements."""
    class MockHelper:
        def learned(self, set_id): return []
        def cleared(self, set_id, sid): return False
        def people_found(self, set_id): return []
        def places_found(self, set_id): return []
        def percent(self, set_id): return 0
        def threads(self, set_id): return set()
        def web_records(self, set_id): return {}
        def sorted_claims(self, set_id): return []
        def myth_records(self, set_id): return {}
        def judged(self, set_id): return set()
        def account_records(self, set_id): return {}
        def decided(self, set_id): return set()
        def review_records(self, set_id): return {}
    helpers = MockHelper()
    state = {"sets": {}, "viewed": []}
    assert achievements.earned(state, {}, helpers) == []


def test_earned_cleared_section_boundary():
    """first_section requires cleared[0] to be True."""
    class MockHelper:
        def learned(self, set_id): return []
        def cleared(self, set_id, sid): return False
        def people_found(self, set_id): return []
        def places_found(self, set_id): return []
        def percent(self, set_id): return 0
        def threads(self, set_id): return set()
        def web_records(self, set_id): return {}
        def sorted_claims(self, set_id): return []
        def myth_records(self, set_id): return {}
        def judged(self, set_id): return set()
        def account_records(self, set_id): return {}
        def decided(self, set_id): return set()
        def review_records(self, set_id): return {}
    helpers = MockHelper()
    cset = type("MockSet", (), {
        "event_ids": lambda self, k: [], "people": None, "places": None,
        "web_relation_ids": lambda self: [], "myth_claim_ids": lambda self: [],
        "passage_keys": lambda self: [], "passage": lambda self, k: {},
        "decisions": [], "decision_ids": lambda self: [], "section_ids": ["s1"]
    })()

    state = {"sets": {"s1": {"solved": {}}}, "viewed": []}
    assert achievements.earned(state, {"s1": cset}, helpers) == []

    def mock_cleared(sid, s): return True
    helpers.cleared = mock_cleared
    earned = achievements.earned(state, {"s1": cset}, helpers)
    assert "first_section" in earned
