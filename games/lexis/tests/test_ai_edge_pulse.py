"""Edge-case tests for pulse.py."""

import pytest
from pulse import spell_number, say_lamps, say_door, MAX_NUMBER


def test_spell_number_zero():
    """spell_number should handle zero correctly."""
    assert spell_number(0) == "0000"


def test_spell_number_max():
    """spell_number should handle the maximum allowed value (MAX_NUMBER)."""
    assert spell_number(MAX_NUMBER) == "0111"


def test_spell_number_below_min_rejected():
    """spell_number should reject values below zero."""
    with pytest.raises(ValueError):
        spell_number(-1)


def test_spell_number_above_max_rejected():
    """spell_number should reject values above MAX_NUMBER."""
    with pytest.raises(ValueError):
        spell_number(MAX_NUMBER + 1)


def test_say_lamps_zero():
    """say_lamps should handle zero lamps."""
    result = say_lamps(0)
    assert isinstance(result, str)
    assert len(result) == 12


def test_say_lamps_max():
    """say_lamps should handle MAX_NUMBER lamps."""
    result = say_lamps(MAX_NUMBER)
    assert isinstance(result, str)
    assert len(result) == 12


def test_say_door_open():
    """say_door should handle the 'open' state."""
    result = say_door("open")
    assert isinstance(result, str)
    assert len(result) == 12


def test_say_door_shut():
    """say_door should handle the 'shut' state."""
    result = say_door("shut")
    assert isinstance(result, str)
    assert len(result) == 12


def test_say_door_invalid_rejected():
    """say_door should reject invalid states."""
    with pytest.raises(ValueError):
        say_door("broken")
