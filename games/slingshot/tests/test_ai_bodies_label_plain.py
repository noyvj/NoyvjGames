"""Tests for label_plain() in bodies.py."""

import bodies


def test_label_plain_for_a_planet():
    """A planet name from the data should be capitalised normally."""
    assert bodies.label_plain("earth") == "Earth"
    assert bodies.label_plain("venus") == "Venus"


def test_label_plain_for_a_moon():
    """A moon name from the data should be capitalised normally."""
    assert bodies.label_plain("phobos") == "Phobos"
    assert bodies.label_plain("deimos") == "Deimos"


def test_label_plain_special_cases():
    """'sun' and 'moon' are handled specially to return exactly 'Sun' and 'Moon'."""
    assert bodies.label_plain("sun") == "Sun"
    assert bodies.label_plain("moon") == "Moon"
