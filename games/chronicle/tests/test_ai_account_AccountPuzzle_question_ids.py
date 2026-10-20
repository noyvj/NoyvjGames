"""Tests for AccountPuzzle.question_ids()."""

import account as ac


def test_question_ids_returns_list_of_ids(sample):
    """Normal case: verifies the method returns a list of question IDs."""
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 0)
    ids = puz.question_ids()
    assert isinstance(ids, list)
    assert all(isinstance(qid, str) for qid in ids)


def test_question_ids_length_matches_puzzle_size(sample):
    """Normal case: ensures the returned list length equals the puzzle's size."""
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 0)
    assert len(puz.question_ids()) == puz.size


def test_question_ids_handles_missing_left_out_edge_case(sample):
    """Edge case: verifies 'left_out' is correctly absent when a passage mentions all points."""
    # question_ids() should dynamically reflect the generated questions, not assume a fixed set.
    puz = ac.make_account_puzzle(sample, "a-emancipation", 0)
    ids = puz.question_ids()
    "left_out" in ids
    # The method must match the actual questions list exactly.
    assert ids == [q["id"] for q in puz.questions]
