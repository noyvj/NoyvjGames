"""Tests for Rng.sample() in gen.py."""


import gen


def test_sample_picks_n_items_when_n_less_than_pool():
    """Normal case: n < len(items). Returns exactly n unique items from the pool."""
    rng = gen.Rng(42)
    pool = [10, 20, 30, 40, 50]
    result = rng.sample(pool, 3)
    assert len(result) == 3
    assert set(result).issubset(set(pool))


def test_sample_returns_all_items_when_n_equals_pool():
    """Normal case: n == len(items). Returns all items from the pool."""
    rng = gen.Rng(42)
    pool = [10, 20, 30]
    result = rng.sample(pool, 3)
    assert len(result) == 3
    assert set(result) == set(pool)


def test_sample_returns_all_items_without_error_when_n_greater_than_pool():
    """Edge case: n > len(items). Returns all items without raising an error."""
    rng = gen.Rng(42)
    pool = [10, 20]
    result = rng.sample(pool, 5)
    assert len(result) == 2
    assert set(result) == set(pool)


def test_sample_is_deterministic_for_same_seed():
    """Determinism: identical seed and inputs yield identical output."""
    pool = [10, 20, 30, 40]
    r1 = gen.Rng(99).sample(pool, 2)
    r2 = gen.Rng(99).sample(pool, 2)
    assert r1 == r2
