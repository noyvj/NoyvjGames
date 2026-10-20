import pytest

import regulars


def test_line_for_returns_first_bond_line():
    """Level 1 line for Mira matches the first element in REGULARS."""
    expected = "Mira smells every berry before she nods. 'Good,' she says, which from her is a speech."
    assert regulars.line_for("mira", 1) == expected


def test_line_for_returns_third_bond_line():
    """Level 3 line for Mira matches the third element in REGULARS."""
    expected = "Mira leaves a pressed leaf in the till: 'For the stall. Yours is better than mine.'"
    assert regulars.line_for("mira", 3) == expected


def test_line_for_returns_correct_line_for_another_regular():
    """Level 2 line for Brandt matches his second story beat."""
    expected = "Brandt says the river taught him patience and the ferry timetable took it back."
    assert regulars.line_for("brandt", 2) == expected


def test_line_for_raises_on_out_of_bounds_level():
    """Passing level 4 (beyond the three bond levels) raises IndexError."""
    with pytest.raises(IndexError):
        regulars.line_for("mira", 4)
