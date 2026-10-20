"""Tests for founding.bonus_text()."""

import pytest

import founding


def test_bonus_text_food_legacy():
    """A valid food legacy returns the correct formatted string."""
    entry = {"id": "seed_stock"}
    assert founding.bonus_text(entry) == "+6 food"


def test_bonus_text_materials_legacy():
    """A valid materials legacy returns the correct formatted string."""
    entry = {"id": "builders_plans"}
    assert founding.bonus_text(entry) == "+8 materials"


def test_bonus_text_tools_legacy():
    """A valid tools legacy correctly singularizes 'tool' via LEGACY_LABEL_UNIT."""
    entry = {"id": "salvage_kit"}
    assert founding.bonus_text(entry) == "+1 tool"


def test_bonus_text_unknown_id_raises_keyerror():
    """An unknown legacy ID raises KeyError, as the function trusts its input."""
    entry = {"id": "nonexistent_legacy"}
    with pytest.raises(KeyError):
        founding.bonus_text(entry)
