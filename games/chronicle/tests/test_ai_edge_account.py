"""Edge-case tests for account.py public functions."""

import pytest

import account as ac


def test_main_rounds_returns_zero_for_missing_account(sample):
    """main_rounds should return 0 when the account does not exist."""
    assert ac.main_rounds(sample, "nonexistent-account") == 0


def test_make_account_puzzle_rejects_negative_round(sample):
    """make_account_puzzle must raise ValueError for negative round numbers."""
    with pytest.raises(ValueError):
        ac.make_account_puzzle(sample, "a-gettysburg", -1)


def test_make_account_puzzle_handles_large_round_via_modulo(sample):
    """A very large round number should wrap around using modulo, not crash."""
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 10**9)
    assert isinstance(puz, ac.AccountPuzzle)
    assert puz.round == 10**9


def test_grade_with_empty_answers_returns_all_empty(sample):
    """grade should mark every question as 'empty' when no answers are provided."""
    puz = ac.make_account_puzzle(sample, "a-gettysburg", 0)
    result = ac.grade(puz, {})
    assert all(q["status"] == "empty" for q in result["questions"])
    assert result["right"] == 0 and result["placed"] == 0


def test_omitted_points_returns_empty_list_when_nothing_is_left_out(sample):
    """omitted_points should return an empty list when the passage mentions every point."""
    a = sample.account("a-gettysburg")
    all_ids = [pt["id"] for pt in a["points"]]
    full_passage = {"id": "test", "mentions": all_ids}
    assert ac.omitted_points(a, full_passage) == []


def test_display_order_returns_all_passage_ids(sample):
    """display_order should return a list containing every passage ID for the account."""
    order = ac.display_order(sample, "a-gettysburg")
    a = sample.account("a-gettysburg")
    assert set(order) == {p["id"] for p in a["passages"]}
