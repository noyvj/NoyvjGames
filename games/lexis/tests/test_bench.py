import pytest
from bench import add_pulses, int_to_pulse, pulse_to_int


def test_pulse_to_int():
    assert pulse_to_int("0000") == 0
    assert pulse_to_int("0111") == 7
    with pytest.raises(ValueError):
        pulse_to_int("1000")


def test_int_to_pulse():
    assert int_to_pulse(0) == "0000"
    assert int_to_pulse(7) == "0111"
    with pytest.raises(ValueError):
        int_to_pulse(8)


def test_add_pulses():
    assert add_pulses("0001", "0010") == "0011"
    assert add_pulses("0100", "0011") == "0111"
    assert add_pulses("0111", "0001") is None
