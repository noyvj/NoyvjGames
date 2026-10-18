"""Tests for orbit.state_at: position and velocity at a given true anomaly."""

import math

import orbit


def test_circular_orbit_at_periapsis():
    """A circular orbit (e=0) should place the probe at distance p on the x-axis with purely tangential velocity."""
    mu = 398600.4418
    p = 10000.0
    e = 0.0
    h_abs = math.sqrt(mu * p)
    phi = 0.0
    sense = 1
    nu = 0.0

    x, y, vx, vy = orbit.state_at(mu, p, e, h_abs, phi, sense, nu)
    assert abs(x - p) < 1e-6
    assert abs(y) < 1e-6
    assert abs(vx) < 1e-6
    expected_v = math.sqrt(mu / p)
    assert abs(vy - expected_v) < 1e-6


def test_elliptical_orbit_at_apoapsis():
    """At apoapsis (nu=pi), distance should be a*(1+e) and velocity purely tangential, matching vis-viva."""
    mu = 1.32712440018e11
    a = 1.5e8
    e = 0.2
    p = a * (1.0 - e ** 2)
    h_abs = math.sqrt(mu * p)
    phi = 0.0
    sense = 1
    nu = math.pi

    x, y, vx, vy = orbit.state_at(mu, p, e, h_abs, phi, sense, nu)
    expected_r = a * (1.0 + e)
    assert abs(x - (-expected_r)) < 1e-3
    assert abs(y) < 1e-3
    assert abs(vx) < 1e-6
    expected_v2 = mu * (2.0 / expected_r - 1.0 / a)
    assert abs(vx ** 2 + vy ** 2 - expected_v2) < 1e-3


def test_high_eccentricity_orbit_at_periapsis():
    """Edge case: highly elliptical orbit (e=0.95) at periapsis (nu=0). vr should be zero, r should equal p."""
    mu = 1.32712440018e11
    a = 1.0e8
    e = 0.95
    p = a * (1.0 - e ** 2)
    h_abs = math.sqrt(mu * p)
    phi = math.pi / 6
    sense = 1
    nu = 0.0

    r_peri = p / (1.0 + e)
    x, y, vx, vy = orbit.state_at(mu, p, e, h_abs, phi, sense, nu)
    assert abs(x - r_peri * math.cos(phi)) < 1e-3
    assert abs(y - r_peri * math.sin(phi)) < 1e-3
    # At periapsis vr=0, so velocity is purely tangential (perpendicular to radius)
    dot = x * vx + y * vy
    assert abs(dot) < 1e-6
    expected_v2 = mu * (2.0 / r_peri - 1.0 / a)
    assert abs(vx ** 2 + vy ** 2 - expected_v2) < 1e-3
