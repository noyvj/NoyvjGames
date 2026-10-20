"""Tests for Notebook.truth()."""

from notebook import Notebook


def test_truth_returns_meaning_for_known_word():
    from pulse import PULSE
    nb = Notebook()
    word = PULSE.words[0]
    assert nb.truth(word.form) == word.meaning


def test_truth_returns_digits_for_number_token():
    from pulse import PULSE
    nb = Notebook()
    # Use a valid number token from the game's data.
    token = "0001"
    assert PULSE.is_number_token(token) is True
    assert nb.truth(token) == str(PULSE.number_value(token))


def test_truth_returns_none_for_unknown_form():
    nb = Notebook()
    assert nb.truth("unknown_form_xyz") is None
