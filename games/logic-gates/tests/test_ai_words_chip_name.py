"""Tests for chip_name() in words.py."""

import levels
import words


def test_chip_name_returns_label_for_known_type():
    """A known chip type should return its label from REGISTRY."""
    # Find a level that actually has chips (Chapter 1 is switches/lamps only).
    ref_level = next(lev for lev in levels.LEVELS if lev.get("ref", {}).get("chips"))
    ref_chip = ref_level["ref"]["chips"][0]
    expected = levels.REGISTRY[ref_chip["type"]]["label"]
    assert words.chip_name(ref_chip) == expected


def test_chip_name_returns_label_for_another_known_type():
    """Another known chip type should also return its REGISTRY label."""
    # Pick a different type from the registry to ensure it's not just matching one entry.
    ref_level = next(lev for lev in levels.LEVELS if lev.get("ref", {}).get("chips"))
    used_type = ref_level["ref"]["chips"][0]["type"]
    other_type = next(k for k in levels.REGISTRY if k != used_type)
    other_chip = {"type": other_type}
    expected = levels.REGISTRY[other_type]["label"]
    assert words.chip_name(other_chip) == expected


def test_chip_name_returns_type_for_unknown_type():
    """An unknown chip type should fall back to returning the type string itself."""
    unknown_chip = {"type": "phantom_gate"}
    assert words.chip_name(unknown_chip) == "phantom_gate"
