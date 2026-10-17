"""Tests for hints.piece_line()."""

import benches
import hints


def test_mirror_slash():
    """A mirror with state 0 should append ', slash'."""
    item = benches.BY_ID["c1-1"].solution[0]
    result = hints.piece_line(item)
    assert result.startswith("Mirror at r")
    assert ", slash" in result


def test_mirror_backslash():
    """A mirror with state 1 should append ', backslash'."""
    item = (3, 4, "mirror", 1)
    result = hints.piece_line(item)
    assert result.startswith("Mirror at r")
    assert ", backslash" in result


def test_prism_left():
    """A prism with state 0 should describe the S beam direction."""
    item = (2, 5, "prism", 0)
    result = hints.piece_line(item)
    assert result.startswith("Prism at r")
    assert "S beam leaves on the left of its travel" in result


def test_absorber_no_suffix():
    """An absorber has no state-dependent suffix; it should just name the piece and cell."""
    item = (1, 2, "absorber", 0)
    result = hints.piece_line(item)
    assert result == "Absorber at row 2, column 3"
