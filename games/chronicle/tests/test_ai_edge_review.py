"""Edge-case tests for review.py."""

import unittest.mock as mock

import review as rv


def test_split_key_handles_edge_cases():
    """Test split_key with empty strings, missing colons, multiple colons, and non-string inputs."""
    assert rv.split_key("") == ("", "")
    assert rv.split_key("no_colon") == ("no_colon", "")
    assert rv.split_key("a:b:c") == ("a", "b:c")
    assert rv.split_key(123) == ("123", "")


def test_is_settled_respects_step_boundary():
    """Test is_settled at the exact ladder length boundary and with empty input."""
    rec = {"step": 4, "due": 0, "last": None, "asked": 0, "right": 0}
    assert not rv.is_settled(rec)
    rec["step"] = 5
    assert rv.is_settled(rec)
    rec["step"] = 100
    assert rv.is_settled(rec)
    assert not rv.is_settled({})


def test_after_answer_clamps_gap_when_step_exceeds_ladder():
    """Test that after_answer uses the maximum ladder gap when step goes past the top."""
    rec = {"step": 5, "due": 0, "last": None, "asked": 0, "right": 0}
    # Step is already at the top (5). Climbing again should use the last ladder value (30), not index out of range.
    rec = rv.after_answer(rec, 10, True)
    assert rec["step"] == 6 and rec["due"] == 40 and rec["right"] == 1


def test_interval_text_handles_zero_and_negative():
    """Test interval_text with zero, one, negative, and large day values."""
    assert rv.interval_text(0) == "in 0 days"
    assert rv.interval_text(1) == "tomorrow"
    assert rv.interval_text(-5) == "in -5 days"
    assert rv.interval_text(99999) == "in 99999 days"


def test_due_keys_respects_day_and_empty_srs():
    """Test due_keys with empty srs, negative day, and various due dates."""
    class FakeCset:
        event_order = ["e1", "e2"]
        def myth_claim_ids(self): return []
        def web_relation_ids(self): return []
        def decision_ids(self): return []

    prog = {"learned": ["e1", "e2"], "sorted": set(), "threads": set(), "decided": {}}
    cset = FakeCset()

    assert rv.due_keys(cset, prog, {}, 0) == ["ev:e1", "ev:e2"]
    assert rv.due_keys(cset, prog, {}, -1) == []

    srs = {"ev:e1": {"due": 5}, "ev:e2": {"due": 10}}
    assert rv.due_keys(cset, prog, srs, 3) == []
    assert rv.due_keys(cset, prog, srs, 5) == ["ev:e1"]
    assert rv.due_keys(cset, prog, srs, 10) == ["ev:e1", "ev:e2"]


def test_ready_questions_handles_limit_correctly():
    """Test ready_questions limit=0 (falsy) vs limit=1, and empty inputs."""
    fake_cset = object()
    fake_prog = {}
    fake_srs = {}
    fake_labels = {}

    with mock.patch.object(rv, 'due_keys', return_value=["k1", "k2"]):
        with mock.patch.object(rv, 'make_question', return_value={"key": "k1"}):
            res0 = rv.ready_questions(fake_cset, fake_prog, fake_srs, 0, fake_labels, limit=0)
            assert len(res0) == 2

            res1 = rv.ready_questions(fake_cset, fake_prog, fake_srs, 0, fake_labels, limit=1)
            assert len(res1) == 1
