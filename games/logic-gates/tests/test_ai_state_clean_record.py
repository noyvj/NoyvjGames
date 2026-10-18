"""Tests for clean_record() in state.py."""


import state


def test_clean_record_accepts_valid_fields():
    data = {"solved": True, "chips": 3, "par": True, "hints": 2, "answer": False}
    rec = state.clean_record(data)
    assert rec == {"solved": True, "chips": 3, "par": True, "hints": 2, "answer": False}


def test_clean_record_falls_back_to_defaults_for_missing_fields():
    data = {"solved": True}
    rec = state.clean_record(data)
    assert rec["solved"] is True
    assert rec["chips"] is None
    assert rec["par"] is False
    assert rec["hints"] == 0
    assert rec["answer"] is False


def test_clean_record_clamps_and_ignores_invalid_values():
    data = {"solved": "yes", "chips": 600, "par": True, "hints": -5, "answer": None}
    rec = state.clean_record(data)
    assert rec["solved"] is False
    assert rec["chips"] == 500
    assert rec["par"] is False
    assert rec["hints"] == 0
    assert rec["answer"] is False
