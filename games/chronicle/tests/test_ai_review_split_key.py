"""Tests for split_key() in review.py."""

import review as rv


def test_split_key_returns_kind_and_ident_for_ev_key():
    key = "ev:e-kennedy"
    kind, ident = rv.split_key(key)
    assert kind == "ev" and ident == "e-kennedy"


def test_split_key_returns_kind_and_ident_for_my_key():
    key = "my:c-e-gettysburg-tradition"
    kind, ident = rv.split_key(key)
    assert kind == "my" and ident == "c-e-gettysburg-tradition"


def test_split_key_handles_missing_colon_as_empty_ident():
    key = "ev"
    kind, ident = rv.split_key(key)
    assert kind == "ev" and ident == ""
