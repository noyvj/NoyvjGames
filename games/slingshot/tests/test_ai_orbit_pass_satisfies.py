"""Tests for orbit.pass_satisfies: does a pass result meet a goal?"""

import orbit


def test_flyby_goal_satisfied_when_rp_is_within_range():
    """A flyby goal is met when the probe's closest approach distance falls between min and within."""
    goal = {"kind": "flyby", "body": "earth", "min": 6000.0, "within": 8000.0}
    res = {"child": "earth", "rp": 7000.0, "k_in": 100}
    assert orbit.pass_satisfies(goal, res) is True


def test_flyby_goal_not_met_when_probe_impacts_body():
    """An impact always overrides a flyby goal, even if rp would otherwise be in range."""
    goal = {"kind": "flyby", "body": "earth", "min": 6000.0, "within": 8000.0}
    res = {"child": "earth", "rp": 7000.0, "impact": True, "k_in": 100}
    assert orbit.pass_satisfies(goal, res) is False


def test_capture_goal_satisfied_with_correct_orbit_and_sense():
    """A capture goal is met when captured is true, q and big_q are within bounds, and sense matches."""
    goal = {
        "kind": "capture",
        "body": "mars",
        "q": [3000.0, 5000.0],
        "big_q": 10000.0,
        "sense": "pro"
    }
    res = {
        "child": "mars",
        "captured": True,
        "q": 4000.0,
        "big_q": 8000.0,
        "sense": 1,
        "k_in": 200
    }
    assert orbit.pass_satisfies(goal, res) is True


def test_pass_fails_when_goal_body_does_not_match_res_child():
    """Edge case: the goal targets a different body than the one being passed."""
    goal = {"kind": "flyby", "body": "venus"}
    res = {"child": "earth", "rp": 7000.0, "k_in": 100}
    assert orbit.pass_satisfies(goal, res) is False
