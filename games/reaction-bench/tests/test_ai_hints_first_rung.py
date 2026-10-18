"""Tests for hints.first_rung()."""


import hints


def test_normal_difficulty_starts_at_rung_one():
    """Normal difficulty begins with the nudge (rung 1)."""
    assert hints.first_rung("normal") == 1


def test_hard_difficulty_starts_at_rung_one():
    """Hard difficulty also begins with the nudge (rung 1)."""
    assert hints.first_rung("hard") == 1


def test_easy_difficulty_opens_two_rungs():
    """Easy difficulty opens both the nudge and the hint together (rung 2)."""
    assert hints.first_rung("easy") == 2


def test_unknown_difficulty_defaults_to_rung_one():
    """Any unrecognized difficulty string falls back to rung 1."""
    assert hints.first_rung("legendary") == 1
