"""Tests for atlas.label()."""

import atlas


def test_label_returns_correct_name_for_a_moon():
    assert atlas.label("moon") == "The Moon"


def test_label_returns_correct_name_for_a_planet():
    assert atlas.label("venus") == "Venus"


def test_label_handles_destination_with_apostrophe():
    assert atlas.label("mercury") == "Mercury's orbit"
