"""Tests for soi_radius() in bodies.py."""


import bodies_data as D
from bodies import soi_radius


def test_earth_soi_matches_expected_range():
    """Earth's sphere of influence should be around 925,000 km."""
    a = D.PLANETS["earth"][2] * D.AU_KM
    gm_body = D.PLANETS["earth"][0]
    gm_parent = D.GM_SUN
    result = soi_radius(a, gm_body, gm_parent)
    assert abs(result - 925000) < 1000


def test_moon_soi_matches_expected_range():
    """The Moon's sphere of influence should be around 66,000 km."""
    a = D.MOONS["moon"][3]
    gm_body = D.MOONS["moon"][1]
    gm_parent = D.PLANETS["earth"][0]
    result = soi_radius(a, gm_body, gm_parent)
    assert abs(result - 66000) < 1000


def test_equal_gms_returns_a_km():
    """When the two bodies have equal gravitational parameters, SOI equals the orbital radius."""
    a = 1000.0
    gm = 100.0
    result = soi_radius(a, gm, gm)
    assert result == a
