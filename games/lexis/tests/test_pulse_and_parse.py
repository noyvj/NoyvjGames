import pytest

from lang import decode_number
from parse import SignalError, parse, tokenize
from pulse import MAX_NUMBER, PULSE, say_door, say_lamps, spell_number


def test_every_number_round_trips_through_its_spelling():
    for n in range(MAX_NUMBER + 1):
        token = spell_number(n)
        assert len(token) == PULSE.token_len
        assert PULSE.is_number_token(token)
        assert PULSE.number_value(token) == n


def test_numbers_outside_three_marks_cannot_be_spelled():
    for bad in (-1, 8, 100):
        with pytest.raises(ValueError):
            spell_number(bad)


def test_word_forms_are_unique_and_never_look_like_numbers():
    forms = [w.form for w in PULSE.words]
    assert len(forms) == len(set(forms))
    for form in forms:
        assert len(form) == PULSE.token_len
        assert not PULSE.is_number_token(form)


def test_the_three_wrong_number_rules_disagree_with_the_true_one_somewhere():
    for wrong in ("binary_lsb", "popcount"):
        assert any(decode_number(format(n, "03b"), wrong) != n for n in range(8)), wrong


def test_parses_lamp_and_door_sentences():
    assert parse(say_lamps(5), PULSE).noun == "lamp" and parse(say_lamps(5), PULSE).value == 5
    sentence = parse(say_door("open"), PULSE)
    assert (sentence.noun, sentence.value) == ("door", "open")
    assert parse(say_door("shut"), PULSE).value == "shut"


@pytest.mark.parametrize("marks,reason", [
    ("", "silence"),
    ("10x0", "bad_mark"),
    ("100", "cut_off"),
    ("1000" + "0011", "no_end"),
    ("1000" + "1111" + "0011" + "1111", "early_end"),
    ("1111", "shape"),
    ("1000" + "0011" + "0001" + "1111", "shape"),
    ("0011" + "0011" + "1111", "no_thing"),
    ("1010" + "0011" + "1111", "no_thing"),
    ("1100" + "0011" + "1111", "no_thing"),
    ("1000" + "1010" + "1111", "lamp_needs_number"),
    ("1001" + "0011" + "1111", "door_needs_state"),
    ("1001" + "1000" + "1111", "door_needs_state"),
])
def test_a_signal_the_language_cannot_say_gets_an_in_world_answer(marks, reason):
    with pytest.raises(SignalError) as err:
        parse(marks, PULSE)
    assert err.value.reason == reason
    assert err.value.text and "error" not in err.value.text.lower() and "exception" not in err.value.text.lower()


def test_tokenize_splits_into_fixed_width_tokens():
    assert tokenize("10000011" + "1111", PULSE) == ["1000", "0011", "1111"]
