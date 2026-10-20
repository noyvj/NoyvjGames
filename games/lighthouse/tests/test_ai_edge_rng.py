"""Edge-case tests for rng.py."""

import rng


def test_mix_no_parts_and_bools():
    """mix() with zero arguments returns a constant, and booleans are treated as ints."""
    assert rng.mix() == rng.mix()
    assert isinstance(rng.mix(), int)
    assert rng.mix(True) == rng.mix(1)
    assert rng.mix(False) == rng.mix(0)


def test_unit_empty_parts_is_deterministic():
    """unit() called without parts must return the same float in [0, 1) every time."""
    val = rng.unit()
    assert 0.0 <= val < 1.0
    assert val == rng.unit()


def test_rint_equal_bounds_and_negative_range():
    """When lo and hi are equal, rint returns that value; negative ranges stay within bounds."""
    for _ in range(10):
        assert rng.rint(42, 42, "edge") == 42
    # rng is deterministic, so we vary the seed to check coverage and bounds
    values = {rng.rint(-5, -1, f"neg_{i}") for i in range(100)}
    assert all(-5 <= v <= -1 for v in values)


def test_pick_single_element_returns_it():
    """pick() on a list with one item must return that item regardless of the random seed."""
    assert rng.pick(["only_one"], "key") == "only_one"


def test_weighted_zero_first_weight_skips_to_last():
    """weighted() with [0, 1] should pick the second option because r < acc never triggers for the first."""
    results = [rng.weighted(["a", "b"], [0, 1], "test") for _ in range(100)]
    assert all(r == "b" for r in results)
