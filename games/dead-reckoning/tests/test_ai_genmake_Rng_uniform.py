import genmake


def test_uniform_returns_value_within_bounds():
    """A call to uniform(lo, hi) stays inside [lo, hi]."""
    rng = genmake.Rng(seed=42)
    lo, hi = 10.0, 20.0
    val = rng.uniform(lo, hi)
    assert lo <= val <= hi


def test_uniform_is_deterministic_for_same_seed():
    """The same seed produces the same sequence of values."""
    rng1 = genmake.Rng(seed=99)
    rng2 = genmake.Rng(seed=99)
    assert rng1.uniform(0.0, 100.0) == rng2.uniform(0.0, 100.0)


def test_uniform_handles_equal_bounds():
    """When lo equals hi, the result is exactly that value."""
    rng = genmake.Rng(seed=7)
    val = rng.uniform(5.0, 5.0)
    assert val == 5.0
