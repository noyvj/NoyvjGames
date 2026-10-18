"""Tests for atlas.card(): real numbers for destinations."""

import atlas
import bodies_data as D


def test_card_for_a_planet_returns_four_lines_and_correct_source():
    """Normal case: a planet card has Size, Orbit, Pull, In the game lines and JPL source."""
    lines, source = atlas.card("earth")
    assert len(lines) == 4
    titles = [t for t, _ in lines]
    assert "Size" in titles and "Orbit" in titles and "Pull" in titles and "In the game" in titles
    assert source.startswith("JPL Planetary Physical Parameters")


def test_card_for_a_small_moon_mentions_rendezvous():
    """Edge case: a moon with no usable SOI returns rendezvous text instead of sphere of influence."""
    lines, source = atlas.card("phobos")
    assert len(lines) == 4
    _, text = [line for line in lines if line[0] == "In the game"][0]
    assert "rendezvous" in text.lower()
    assert source.startswith("JPL Planetary Satellite Physical Parameters")


def test_card_for_sunward_returns_one_line_with_correct_title():
    """Edge case: an unknown destination falls back to the Sunward card with one line."""
    lines, source = atlas.card("sun")
    assert len(lines) == 1
    assert lines[0][0] == "Sunward"
    assert "99.8 percent" in lines[0][1]
    assert source == "JPL Astrodynamic Parameters, read %s." % D.READ
