"""Tests for orbit.elements(): orbital elements from a state vector."""

import math

import bodies_data as D
import orbit


def test_circular_orbit_has_zero_eccentricity_and_correct_radius():
    mu = D.GM_SUN
    r = 1e8
    v = math.sqrt(mu / r)
    res = orbit.elements(mu, r, 0.0, 0.0, v)
    assert abs(res["r"] - r) < 1e-6
    assert abs(res["e"]) < 1e-9
    assert abs(res["p"] - r) < 1e-6
    assert abs(res["energy"] + mu / (2 * r)) < 1e-9
    assert res["phi"] == 0.0


def test_elliptical_orbit_at_periapsis_has_correct_eccentricity_and_energy():
    mu = D.GM_SUN
    a, e_val = 2e8, 0.5
    rp = a * (1 - e_val)
    vp = math.sqrt(mu * (1 + e_val) / rp)
    res = orbit.elements(mu, rp, 0.0, 0.0, vp)
    assert abs(res["e"] - e_val) < 1e-9
    assert abs(res["r"] - rp) < 1e-6
    assert abs(res["energy"] + mu / (2 * a)) < 1e-9


def test_hyperbolic_trajectory_has_positive_energy_and_eccentricity_greater_than_one():
    mu = D.GM_SUN
    r = 1e8
    v = math.sqrt(3.0 * mu / r)
    res = orbit.elements(mu, r, 0.0, 0.0, v)
    assert res["energy"] > 0
    assert res["e"] > 1.0
    assert abs(res["r"] - r) < 1e-6
