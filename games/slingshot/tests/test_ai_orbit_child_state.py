"""Tests for orbit.child_state."""

import math

import missions
import orbit


def _make_scene(mid):
    m = missions.BY_ID[mid]
    return orbit.make_scene(m["scene"])


def test_child_state_returns_correct_position_and_velocity_at_step_zero():
    """At step 0, child_state should return the initial position and velocity from the scene's precomputed arrays."""
    sc = _make_scene("c1m1")
    cid = sc["children"][0]["id"]
    x, y, vx, vy = orbit.child_state(sc, cid, 0)
    assert math.isclose(x, sc["by_id"][cid]["cx"][0])
    assert math.isclose(y, sc["by_id"][cid]["cy"][0])
    assert math.isclose(vx, -sc["by_id"][cid]["n"] * y)
    assert math.isclose(vy, sc["by_id"][cid]["n"] * x)


def test_child_state_returns_correct_values_at_mid_step():
    """At a valid mid-step index, child_state should return the precomputed position and derived velocity."""
    sc = _make_scene("c1m1")
    cid = sc["children"][0]["id"]
    k = sc["steps"] // 2
    x, y, vx, vy = orbit.child_state(sc, cid, k)
    assert math.isclose(x, sc["by_id"][cid]["cx"][k])
    assert math.isclose(y, sc["by_id"][cid]["cy"][k])
    assert math.isclose(vx, -sc["by_id"][cid]["n"] * y)
    assert math.isclose(vy, sc["by_id"][cid]["n"] * x)


def test_child_state_clamps_out_of_bounds_k():
    """child_state should clamp k to [0, steps + 1] and return the corresponding state."""
    sc = _make_scene("c1m1")
    cid = sc["children"][0]["id"]
    steps = sc["steps"]

    # Negative k clamps to 0
    x_neg, y_neg, _, _ = orbit.child_state(sc, cid, -5)
    x_0, y_0, _, _ = orbit.child_state(sc, cid, 0)
    assert math.isclose(x_neg, x_0) and math.isclose(y_neg, y_0)

    # k > steps + 1 clamps to steps + 1
    x_hi, y_hi, _, _ = orbit.child_state(sc, cid, steps + 10)
    x_max, y_max, _, _ = orbit.child_state(sc, cid, steps + 1)
    assert math.isclose(x_hi, x_max) and math.isclose(y_hi, y_max)
