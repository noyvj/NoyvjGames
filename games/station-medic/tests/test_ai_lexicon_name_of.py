"""Tests for lexicon.name_of()."""

import lexicon as lx


def test_name_of_returns_sign_name():
    """name_of('sign', ...) returns the human-readable sign name."""
    assert lx.name_of("sign", "flushed") == "Flushed"


def test_name_of_returns_item_name():
    """name_of('item', ...) returns the human-readable item name."""
    assert lx.name_of("item", "roll") == "Paper roll"


def test_name_of_returns_test_and_tx_names():
    """name_of('test', ...) and name_of('tx', ...) return their respective names."""
    assert lx.name_of("test", "dye") == "Dye strip"
    assert lx.name_of("tx", "tonic") == "Slate tonic"


def test_name_of_falls_back_to_ident_for_unknown_kind():
    """name_of('unknown', ...) returns the ident unchanged."""
    assert lx.name_of("unknown_kind", "foo") == "foo"
