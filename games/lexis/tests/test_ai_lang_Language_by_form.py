
from pulse import PULSE


def test_by_form_returns_the_word_when_it_exists():
    """Normal case: look up a known word by its exact form."""
    target = PULSE.words[0]
    result = PULSE.by_form(target.form)
    assert result is target


def test_by_form_finds_another_known_word():
    """Normal case: look up a different known word by its form."""
    target = PULSE.words[-1]
    result = PULSE.by_form(target.form)
    assert result is target


def test_by_form_returns_none_for_unknown_form():
    """Edge case: a form that does not belong to any word returns None."""
    # "0000" is a number token (value 0), not a word in the language
    result = PULSE.by_form("0000")
    assert result is None
