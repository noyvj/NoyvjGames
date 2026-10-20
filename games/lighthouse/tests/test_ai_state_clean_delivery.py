"""Tests for clean_delivery() in state.py."""

from data import CRATE_KINDS
from state import clean_delivery


def test_normal_delivery_preserves_values_and_text():
    raw = {"items": {k: 10 for k in CRATE_KINDS}, "text": "A fresh crate of supplies arrived today."}
    result = clean_delivery(raw)
    assert result is not None
    assert all(result["items"][k] == 10 for k in CRATE_KINDS)
    assert result["text"] == "A fresh crate of supplies arrived today."


def test_delivery_clamps_values_and_truncates_text():
    raw = {"items": {k: -5 if i == 0 else 1500 for i, k in enumerate(CRATE_KINDS)}, "text": "A" * 300}
    result = clean_delivery(raw)
    assert result is not None
    assert all(result["items"][k] == (0 if i == 0 else 999) for i, k in enumerate(CRATE_KINDS))
    assert len(result["text"]) == 200


def test_missing_items_default_to_zero():
    raw = {"items": {}, "text": "Empty crate."}
    result = clean_delivery(raw)
    assert result is not None
    assert all(0 <= v <= 999 for v in result["items"].values())


def test_empty_or_none_input_returns_none():
    assert clean_delivery({}) is None
    assert clean_delivery(None) is None
