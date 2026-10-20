import pytest

from lang import decode_number
from pulse import PULSE


def test_decode_number_rejects_empty_bits():
    """decode_number raises ValueError when given an empty bits string."""
    with pytest.raises(ValueError):
        decode_number("", "binary_msb")


def test_decode_number_rejects_unknown_rule():
    """decode_number raises ValueError for unsupported rule names."""
    with pytest.raises(ValueError):
        decode_number("101", "unknown_rule")


def test_decode_number_handles_zero_and_max_values():
    """All-zero bits decode to 0; all-one bits decode to the maximum for that length."""
    assert decode_number("000", "binary_msb") == 0
    assert decode_number("111", "binary_msb") == 7


def test_is_number_token_rejects_invalid_tokens():
    """is_number_token returns False for empty, short, or wrong-class-mark tokens."""
    assert PULSE.is_number_token("") is False
    assert PULSE.is_number_token("0") is False
    assert PULSE.is_number_token("1000") is False


def test_is_number_token_accepts_valid_tokens():
    """is_number_token returns True for correctly formatted number tokens."""
    assert PULSE.is_number_token("0000") is True
    assert PULSE.is_number_token("0111") is True


def test_number_value_returns_boundary_values():
    """number_value should return 0 for the smallest token and max for the largest."""
    assert PULSE.number_value("0000") == 0
    assert PULSE.number_value("0111") == 7


def test_by_form_returns_none_for_missing_form():
    """by_form returns None when the form does not match any word."""
    assert PULSE.by_form("9999") is None


def test_by_id_raises_keyerror_for_missing_id():
    """by_id raises KeyError when the id does not exist in the language."""
    with pytest.raises(KeyError):
        PULSE.by_id("nonexistent_word")
