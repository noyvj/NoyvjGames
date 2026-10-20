import pytest

from pulse import PULSE


def test_by_id_returns_the_matching_word():
    # Pick a real word from the Pulse language data
    target = PULSE.words[0]
    assert PULSE.by_id(target.id) == target


def test_by_id_returns_different_words_for_different_ids():
    # Ensure it correctly distinguishes between two distinct words
    w1, w2 = PULSE.words[0], PULSE.words[-1]
    if w1.id == w2.id:
        pytest.skip("Language has fewer than two words")
    assert PULSE.by_id(w1.id) == w1
    assert PULSE.by_id(w2.id) == w2


def test_by_id_raises_KeyError_for_unknown_id():
    # Passing an id that does not exist in the language should raise KeyError
    with pytest.raises(KeyError):
        PULSE.by_id("nonexistent_word")
