"""Tests for button_label() in hints.py."""


import hints


def test_button_label_starts_with_suggestion():
    """Rung 0 always offers the initial suggestion regardless of stage."""
    assert hints.button_label(0, hints.STAGE_CHOOSE) == "Would you like a suggestion?"
    assert hints.button_label(0, hints.STAGE_DIALS) == "Would you like a suggestion?"


def test_button_label_second_press_is_another_hint():
    """Rung 1 always offers 'Another hint' regardless of stage."""
    assert hints.button_label(1, hints.STAGE_CHOOSE) == "Another hint"
    assert hints.button_label(1, hints.STAGE_DIALS) == "Another hint"


def test_button_label_third_press_in_choose_stage():
    """Rung 2 in the choose stage offers to pick the list."""
    assert hints.button_label(2, hints.STAGE_CHOOSE) == "Another hint: choose it for me"


def test_button_label_third_press_in_dials_stage_edge_case():
    """Rung 2 in the dials stage offers to set the dials (edge case: different wording)."""
    assert hints.button_label(2, hints.STAGE_DIALS) == "Another hint: set the dials for me"
