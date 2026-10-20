"""Edge-case tests for lexicon.py."""

import pytest

import lexicon as lx


def test_name_of_returns_correct_names_for_all_known_kinds():
    """Verify name_of returns the exact stored names for valid inputs from the lexicon."""
    assert lx.name_of("sign", "flushed") == "Flushed"
    assert lx.name_of("item", "roll") == "Paper roll"
    assert lx.name_of("test", "dye") == "Dye strip"
    assert lx.name_of("tx", "tonic") == "Slate tonic"
    assert lx.name_of("cond", "coil") == "Coil Fever"


def test_name_of_falls_back_to_ident_for_unknown_kind():
    """When kind is not recognized, name_of returns the ident unchanged."""
    assert lx.name_of("unknown_kind", "some_id") == "some_id"
    assert lx.name_of("", "some_id") == "some_id"


def test_name_of_handles_empty_and_zero_inputs():
    """Empty strings and zero should not raise and fall back gracefully."""
    assert lx.name_of("", "") == ""
    assert lx.name_of("sign", "") == ""
    assert lx.name_of("item", 0) == 0


def test_name_of_with_missing_ident_for_sign_and_item_returns_ident():
    """For sign and item kinds, missing idents fall back to the ident itself."""
    assert lx.name_of("sign", "nonexistent") == "nonexistent"
    assert lx.name_of("item", "missing_shelf") == "missing_shelf"


def test_name_of_with_missing_ident_for_test_tx_cond_raises_keyerror():
    """For test, tx, and cond kinds, missing idents are rejected with KeyError."""
    with pytest.raises(KeyError):
        lx.name_of("test", "fake_scan")
    with pytest.raises(KeyError):
        lx.name_of("tx", "fake_treatment")
    with pytest.raises(KeyError):
        lx.name_of("cond", "fake_condition")
