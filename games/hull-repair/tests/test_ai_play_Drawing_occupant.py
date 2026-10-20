"""Tests for Drawing.occupant() method."""

import pytest

import play
import rules


@pytest.fixture
def simple_board():
    """A simple 5x5 board with two lines A and B crossing on a bridge."""
    return rules.Board({
        "id": "test",
        "rows": ["A...a", "B...b", ".....", ".....", "....."]
    })


@pytest.fixture
def bridge_board():
    """A board with a bridge where two lines cross."""
    return rules.Board({
        "id": "bridge",
        "rows": ["A...a", "B.=.b", ".....", ".....", "....."]
    })


def test_occupant_returns_line_letter_for_regular_cell(simple_board):
    """Test that occupant returns the correct line letter for a regular cell."""
    d = play.Drawing(simple_board)
    d.paths = {"A": [(0, 0), (0, 1), (0, 2)], "B": [(1, 0), (1, 1), (1, 2)]}

    assert d.occupant((0, 1)) == "A"
    assert d.occupant((1, 1)) == "B"
    assert d.occupant((2, 2)) is None


def test_occupant_returns_none_for_empty_cell(simple_board):
    """Test that occupant returns None for an empty cell."""
    d = play.Drawing(simple_board)
    d.paths = {"A": [(0, 0), (0, 1)]}

    assert d.occupant((2, 2)) is None
