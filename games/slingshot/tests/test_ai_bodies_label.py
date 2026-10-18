"""Tests for bodies.label()."""

import bodies


def test_label_sun_returns_the_Sun():
    assert bodies.label("sun") == "the Sun"


def test_label_moon_returns_the_Moon():
    assert bodies.label("moon") == "the Moon"


def test_label_planet_capitalizes_name():
    assert bodies.label("mars") == "Mars"
    assert bodies.label("venus") == "Venus"


def test_label_unknown_capitalizes_name():
    assert bodies.label("phobos") == "Phobos"
