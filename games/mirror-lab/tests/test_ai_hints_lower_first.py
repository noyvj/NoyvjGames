"""Tests for hints.lower_first()."""

import pytest

import benches
import hints


def test_normal_capital_letter_is_lowered():
    """A standard piece line starting with a capital letter gets its first character lowered."""
    input_str = hints.piece_line(benches.BY_ID["c1-1"].solution[0])
    assert hints.lower_first(input_str) == input_str[0].lower() + input_str[1:]


def test_s_beam_prefix_is_unchanged():
    """Strings starting with 'S ' are left exactly as they are."""
    assert hints.lower_first("S beam leaves on the left of its travel") == "S beam leaves on the left of its travel"


def test_l_beam_prefix_is_unchanged():
    """Strings starting with 'L ' are left exactly as they are."""
    assert hints.lower_first("L beam leaves on the right of its travel") == "L beam leaves on the right of its travel"


def test_empty_string_raises_index_error():
    """Passing an empty string hits text[0] and raises IndexError."""
    with pytest.raises(IndexError):
        hints.lower_first("")
