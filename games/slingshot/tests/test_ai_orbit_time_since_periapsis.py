"""Tests for orbit.time_since_periapsis."""

import math

import bodies_data as D
import orbit


def test_ellipse_nu_zero_returns_zero():
    """At periapsis (nu=0) the time since periapsis must be zero."""
    mu = D.GM_SUN
    p, e = 1e6, 0.5
    assert orbit.time_since_periapsis(mu, p, e, 0.0) == 0.0


def test_ellipse_nu_pi_half_is_positive():
    """For an ellipse at nu=pi/2 the time since periapsis is positive."""
    mu = D.GM_SUN
    p, e = 1e6, 0.5
    t = orbit.time_since_periapsis(mu, p, e, math.pi / 2.0)
    assert t > 0


def test_hyperbola_nu_positive_is_positive():
    """For a hyperbolic trajectory at nu=pi/4 the time since periapsis is positive."""
    mu = D.GM_SUN
    p, e = 1e6, 1.5
    t = orbit.time_since_periapsis(mu, p, e, math.pi / 4.0)
    assert t > 0


def test_edge_case_circular_orbit_e_zero():
    """A circular orbit (e=0) should return time proportional to nu."""
    mu = D.GM_SUN
    p = 1e6
    e = 0.0
    nu = math.pi / 2.0
    t = orbit.time_since_periapsis(mu, p, e, nu)
    a = p
    expected = nu * math.sqrt(a ** 3 / mu)
    assert abs(t - expected) < 1e-6
