"""Edge-case tests for hints.py public functions."""


import hints
import reactions


def test_stage_handles_falsy_and_truthy_inputs():
    """Test stage() with empty, zero, and truthy values."""
    assert hints.stage(None) == "choose"
    assert hints.stage(0) == "choose"
    assert hints.stage("") == "choose"
    assert hints.stage(False) == "choose"
    assert hints.stage(True) == "dials"
    assert hints.stage([1]) == "dials"


def test_rung_cap_and_first_rung_with_valid_difficulties():
    """Test rung_cap() and first_rung() with the three valid difficulty levels."""
    for diff in ("easy", "normal", "hard"):
        assert hints.rung_cap(diff) in (2, 3)
        assert hints.first_rung(diff) in (1, 2)
    assert hints.rung_cap("hard") == 2
    assert hints.first_rung("easy") == 2
    assert hints.rung_cap("normal") == 3
    assert hints.first_rung("normal") == 1


def test_rung_cap_and_first_rung_with_invalid_inputs():
    """Test rung_cap() and first_rung() falling back to defaults for invalid inputs."""
    for invalid in (None, "", "legendary", 0, 1):
        assert hints.rung_cap(invalid) == 3
        assert hints.first_rung(invalid) == 1


def test_button_label_returns_expected_strings():
    """Test button_label() at its boundary rung values and both stages."""
    assert hints.button_label(0, "choose") == "Would you like a suggestion?"
    assert hints.button_label(1, "choose") == "Another hint"
    assert hints.button_label(2, "choose") == "Another hint: choose it for me"
    assert hints.button_label(2, "dials") == "Another hint: set the dials for me"


def test_dial_texts_returns_none_when_balanced():
    """Test dial_texts() returning None when all coefficients are 1 (balanced)."""
    r = reactions.BY_ID["carbon-dioxide"]
    coefs = [1, 1, 1]
    assert hints.dial_texts(r, coefs) is None


def test_choose_texts_handles_empty_and_full_tried_lists():
    """Test choose_texts() with an empty tried list and a fully exhausted wrong list."""
    r = reactions.BY_ID["methane"]
    nudge, hint, answer, eliminated = hints.choose_texts(r, [])
    assert nudge and hint and answer
    assert eliminated == 0

    all_wrong_indices = [i for i in range(len(r.choices)) if i != r.right]
    _, hint_full, _, elim_full = hints.choose_texts(r, all_wrong_indices)
    assert "is the one that is left" in hint_full
    assert elim_full is None
