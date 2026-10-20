import pytest
from bench import add_pulses, int_to_pulse, pulse_to_int


def test_pulse_to_int_empty_string():
    """Empty string should raise ValueError."""
    with pytest.raises(ValueError):
        pulse_to_int("")


def test_pulse_to_int_zero_input():
    """Zero input '0000' should convert to 0."""
    assert pulse_to_int("0000") == 0


def test_int_to_pulse_smallest_allowed_value():
    """Smallest allowed value 0 should return '0000'."""
    assert int_to_pulse(0) == "0000"


def test_int_to_pulse_largest_allowed_value():
    """Largest allowed value 7 should return '0111'."""
    assert int_to_pulse(7) == "0111"


def test_int_to_pulse_negative_rejected():
    """Negative numbers should raise ValueError."""
    with pytest.raises(ValueError):
        int_to_pulse(-1)


def test_add_pulses_with_zeros():
    """Adding zero to zero should return '0000'."""
    assert add_pulses("0000", "0000") == "0000"
