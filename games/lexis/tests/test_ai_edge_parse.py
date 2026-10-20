import pytest

from parse import SignalError, tokenize, parse
from pulse import PULSE


def test_tokenize_rejects_empty_marks():
    """tokenize should raise SignalError('silence') for an empty string."""
    with pytest.raises(SignalError) as exc_info:
        tokenize("", PULSE)
    assert exc_info.value.reason == "silence"


def test_tokenize_rejects_non_binary_marks():
    """tokenize should raise SignalError('bad_mark') for characters outside '01'."""
    with pytest.raises(SignalError) as exc_info:
        tokenize("1020", PULSE)
    assert exc_info.value.reason == "bad_mark"


def test_tokenize_rejects_partial_tokens():
    """tokenize should raise SignalError('cut_off') when length is not a multiple of token_len."""
    with pytest.raises(SignalError) as exc_info:
        tokenize("100", PULSE)
    assert exc_info.value.reason == "cut_off"


def test_parse_rejects_missing_end_marker():
    """parse should raise SignalError('no_end') when the last token is not the end marker."""
    door_word = next(w for w in PULSE.words if w.id == "door")
    open_word = next(w for w in PULSE.words if w.id == "open")
    marks = door_word.form + open_word.form
    with pytest.raises(SignalError) as exc_info:
        parse(marks, PULSE)
    assert exc_info.value.reason == "no_end"


def test_parse_rejects_early_end_marker():
    """parse should raise SignalError('early_end') when the end marker appears before the last token."""
    door_word = next(w for w in PULSE.words if w.id == "door")
    open_word = next(w for w in PULSE.words if w.id == "open")
    end_word = next(w for w in PULSE.words if w.id == "end")
    # Must end with the end marker, but have it appear earlier to trigger 'early_end'.
    marks = door_word.form + open_word.form + end_word.form + end_word.form
    with pytest.raises(SignalError) as exc_info:
        parse(marks, PULSE)
    assert exc_info.value.reason == "early_end"


def test_parse_accepts_valid_door_sentence():
    """parse should return a Sentence with noun='door' and value='open' for a correctly formed signal."""
    door_word = next(w for w in PULSE.words if w.id == "door")
    open_word = next(w for w in PULSE.words if w.id == "open")
    end_word = next(w for w in PULSE.words if w.id == "end")
    marks = door_word.form + open_word.form + end_word.form
    result = parse(marks, PULSE)
    assert result.noun == "door"
    assert result.value == "open"
