"""Tests for orbit.conic_points: generates points along a conic section."""

import math

import bodies_data as D
import orbit


def test_full_ellipse_arc_returns_closed_loop():
    """A full 360-degree arc on an ellipse should return count+1 points starting and ending at the same rounded coordinates."""
    mu = D.GM_SUN
    p = 10000.0
    e = 0.2
    h_abs = math.sqrt(mu * p)
    phi = 0.0
    sense = 1
    nu_from = 0.0
    nu_to = orbit.TWO_PI
    count = 16

    pts = orbit.conic_points(mu, p, e, h_abs, phi, sense, nu_from, nu_to, count)

    assert len(pts) == count + 1
    assert pts[0] == pts[-1], "Full ellipse should close on itself"


def test_partial_arc_matches_state_at_boundaries():
    """The first and last points of a partial arc must exactly match state_at at nu_from and nu_to, rounded to 0.1."""
    mu = D.GM_SUN
    p = 8000.0
    e = 0.5
    h_abs = math.sqrt(mu * p)
    phi = math.pi / 4
    sense = -1
    nu_from = 0.0
    nu_to = math.pi / 2
    count = 8

    pts = orbit.conic_points(mu, p, e, h_abs, phi, sense, nu_from, nu_to, count)

    assert len(pts) == count + 1

    s_start = orbit.state_at(mu, p, e, h_abs, phi, sense, nu_from)
    expected_start = [round(s_start[0], 1), round(s_start[1], 1)]
    s_end = orbit.state_at(mu, p, e, h_abs, phi, sense, nu_to)
    expected_end = [round(s_end[0], 1), round(s_end[1], 1)]

    assert pts[0] == expected_start
    assert pts[-1] == expected_end


def test_single_interval_returns_two_points():
    """When count is 1, the function should return exactly two points: start and end."""
    mu = D.GM_SUN
    p = 6000.0
    e = 0.3
    h_abs = math.sqrt(mu * p)
    phi = math.pi / 2
    sense = 1
    nu_from = 0.0
    nu_to = math.pi / 4
    count = 1

    pts = orbit.conic_points(mu, p, e, h_abs, phi, sense, nu_from, nu_to, count)

    assert len(pts) == 2
    s_start = orbit.state_at(mu, p, e, h_abs, phi, sense, nu_from)
    expected_start = [round(s_start[0], 1), round(s_start[1], 1)]
    s_end = orbit.state_at(mu, p, e, h_abs, phi, sense, nu_to)
    expected_end = [round(s_end[0], 1), round(s_end[1], 1)]
    assert pts[0] == expected_start
    assert pts[-1] == expected_end
