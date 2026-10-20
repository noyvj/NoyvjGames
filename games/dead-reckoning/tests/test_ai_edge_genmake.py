import gen
from genmake import make_chart, Rng, SPEC


def test_make_chart_accepts_valid_difficulty_and_seed():
    """Valid difficulty (1-5) and seed=0 should not raise and returns a chart or None."""
    for diff in SPEC:
        result = make_chart(diff, 0)
        assert result is None or isinstance(result, dict)


def test_make_chart_rejects_invalid_difficulty():
    """Difficulty outside SPEC keys (0, 6, negative, string) returns None."""
    for bad_diff in (0, 6, -1, "hard", None):
        assert make_chart(bad_diff, 0) is None


def test_make_chart_rejects_non_integer_seed():
    """Seed must be an int. Floats, strings, and bools are rejected."""
    for bad_seed in (0.5, "0", True, False):
        assert make_chart(1, bad_seed) is None


def test_make_chart_rejects_out_of_bounds_seed():
    """Seed must be 0 <= seed < SEED_LIMIT. Boundaries and beyond return None."""
    limit = gen.SEED_LIMIT
    for bad_seed in (-1, limit, limit + 1):
        assert make_chart(1, bad_seed) is None


def test_make_chart_with_two_flag_does_not_crash():
    """Passing two=True with valid inputs should not raise an error."""
    result = make_chart(1, 0, two=True)
    assert result is None or isinstance(result, dict)


def test_rng_uniform_returns_value_in_range():
    """Rng.uniform returns values within the specified range."""
    rng = Rng(42)
    for _ in range(10):
        val = rng.uniform(5.0, 10.0)
        assert 5.0 <= val <= 10.0


def test_rng_pick_returns_item_from_list():
    """Rng.pick returns one of the items in the given list."""
    rng = Rng(42)
    items = ["alpha", "beta", "gamma"]
    for _ in range(10):
        val = rng.pick(items)
        assert val in items
