"""Tests for doctrines.discount_text()."""

import pytest

import doctrines


def test_maritime_discount_text_sorts_by_percentage_descending():
    text = doctrines.discount_text("maritime")
    assert "15% cheaper" in text
    assert "5% cheaper" in text
    assert text.index("15%") < text.index("5%")


def test_scholarly_discount_text_sorts_alphabetically_on_tie():
    text = doctrines.discount_text("scholarly")
    assert "8% cheaper" in text
    parts = [p.strip() for p in text.split(", ")]
    assert len(parts) == 3
    branches_in_text = [p.split(" research")[0] for p in parts]
    assert branches_in_text == sorted(branches_in_text)


def test_invalid_doctrine_id_raises_keyerror():
    with pytest.raises(KeyError):
        doctrines.discount_text("nonexistent")
