"""Tests for is_message() in notebook.py."""

from notebook import is_message


def test_is_message_valid_bridge_format():
    """A normal Bridge message with letters, digits, and spaces should return True."""
    assert is_message("ku p 0011") is True


def test_is_message_with_punctuation():
    """Messages containing punctuation or other non-alphanumeric characters should return False."""
    assert is_message("hello!") is False


def test_is_message_max_length_edge():
    """Exactly 60 alphanumeric characters is the maximum allowed length and should return True."""
    assert is_message("a" * 60) is True
