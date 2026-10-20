"""Edge-case tests for orbit.py."""

import math

import bodies_data as D
import orbit
import pytest


def test_elements_handles_radial_trajectory_with_zero_angular_momentum():
    """For a radial trajectory with h=0 and e>=1, phi points to periapsis (negative x here)."""
    mu = 3.986004418e5  # Earth GM in km^3/s^2
    res = orbit.elements(mu, 1e6, 0.0, 1.0, 0.0)  # vx=1, vy=0 -> h = x*vy - y*vx = 0
    assert res["h"] == pytest.approx(0.0, abs=1e-9)
    assert res["phi"] == pytest.approx(math.pi, abs=1e-9)
    assert res["e"] >= 1.0


def test_pass_through_handles_zero_angular_momentum_as_impact():
    """A trajectory with h ~ 0 falls straight in and should be marked as impact."""
    mu = D.PLANETS["mars"][0]
    radius = 3389.5
    state = (10000.0, 0.0, 3.5, 0.0)  # vx=3.5, vy=0 -> h = 0
    res = orbit.pass_through(mu, radius, state, dv_pass=0.0)
    assert res.get("impact") is True


def test_pass_satisfies_rejects_pass_after_deadline():
    """A pass that occurs after the goal's 'by' step should be rejected."""
    goal = {"kind": "flyby", "body": "mars", "within": 10000.0, "by": 50}
    res = {"child": "mars", "rp": 5000.0, "k_in": 60}
    assert orbit.pass_satisfies(goal, res) is False


def test_hohmann_returns_zero_burns_for_equal_radii():
    """Transferring between the same circular orbit requires no delta-v."""
    mu = D.GM_SUN
    r = 1.496e8  # 1 AU in km
    d1, d2, period = orbit.hohmann(mu, r, r)
    assert d1 == pytest.approx(0.0, abs=1e-9)
    assert d2 == pytest.approx(0.0, abs=1e-9)
    assert period > 0


def test_judge_returns_correct_outcome_for_over_budget_success():
    """When the goal is met but fuel exceeds budget, judge should return 'over_budget'."""
    result = {"ended": "success", "fuel": 5.1}
    assert orbit.judge(result, 5.0) == "over_budget"


def test_judge_returns_miss_for_captured_flight():
    """When the flight ends because the probe was captured but not in the goal orbit, judge returns 'miss'."""
    result = {"ended": "captured", "fuel": 2.0}
    assert orbit.judge(result, 10.0) == "miss"
