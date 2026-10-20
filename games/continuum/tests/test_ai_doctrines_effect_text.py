"""Tests for doctrines.effect_text()."""

import pytest

import doctrines


def test_effect_text_maritime_returns_non_empty_string():
    """Normal case: maritime doctrine yields a formatted effect string."""
    result = doctrines.effect_text("maritime")
    assert isinstance(result, str)
    assert len(result) > 0


def test_effect_text_scholarly_returns_non_empty_string():
    """Normal case: scholarly doctrine yields a formatted effect string."""
    result = doctrines.effect_text("scholarly")
    assert isinstance(result, str)
    assert len(result) > 0


def test_effect_text_invalid_doctrine_raises_keyerror():
    """Edge case: passing an unknown doctrine id propagates the KeyError from DOCTRINES lookup."""
    with pytest.raises(KeyError):
        doctrines.effect_text("unknown_doctrine")
